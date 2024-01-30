"""Controller main entry point."""

import sys
import ssl
import time
import logging
from typing import Optional, Any
from functools import partial
from threading import Lock

import apsw

import rpyc
from rpyc.core import Connection, Service
from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import SSLAuthenticator

import click

from .config import get_controller_config
from .controller import (
    add_setup,
    get_all_setup_names,
    get_setup_dir_tar,
    get_single_available_task,
    set_task_completed,
    add_new_task,
    get_all_completed_tasks,
    set_task_failed,
    set_task_processed,
)
from ..db import setup_db as sdb
from ..db import task_db as tdb

logger = logging.getLogger(__name__)

CONNECT_RETRY_TIME = 300
CONNECT_INTER_RETRY_TIME = 5

DB_LOCK = Lock()

# Main logic
# =============================================================================


class ControllerService(Service):
    def __init__(self):
        self.conn: Optional[Connection] = None
        self.db_con: Optional[apsw.Connection] = None
        self.config = get_controller_config()

    def on_connect(self, conn: Connection) -> None:
        self.conn = conn

        db_con_path = self.config.setup_root / "controller.db"
        db_con_path = str(db_con_path)
        self.db_con = apsw.Connection(db_con_path)
        # self.db_con.execute("pragma busy_timeout=1800;")
        self.db_con.setbusytimeout(1800 * 1000)

    def on_disconnect(self, _: Connection) -> None:
        assert self.conn is not None
        assert self.db_con is not None

        self.conn = None

        self.db_con.close()
        self.db_con = None

    # Setup distribution

    def exposed_add_setup(self, setup_name: str, setup_dir_tar: bytes) -> None:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return add_setup(
                    config=self.config,
                    db_con=self.db_con,
                    setup_name=setup_name,
                    setup_dir_tar=setup_dir_tar,
                )

    def exposed_get_all_setup_names(self) -> list[str]:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return get_all_setup_names(db_con=self.db_con)
            return []

    def exposed_get_setup_dir_tar(self, setup_name: str) -> bytes:
        return get_setup_dir_tar(config=self.config, setup_name=setup_name)

    # Agent - Controller Interaction

    def exposed_get_single_available_task(
        self, cluster: str
    ) -> Optional[tuple[str, str, str, int]]:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return get_single_available_task(
                    config=self.config, db_con=self.db_con, cluster=cluster
                )

    def exposed_set_task_completed(self, task_id: str, task_result_json: str) -> None:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return set_task_completed(
                    db_con=self.db_con, task_id=task_id, task_result_json=task_result_json
                )

    def exposed_set_task_failed(self, task_id: str) -> None:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return set_task_failed(db_con=self.db_con, task_id=task_id)

    # Task Source - Controller Interaction

    def exposed_add_new_task(
        self,
        task_id: str,
        task_type: str,
        task_data_json: str,
        task_priority: int,
    ) -> None:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return add_new_task(
                    db_con=self.db_con,
                    task_id=task_id,
                    task_type=task_type,
                    task_data_json=task_data_json,
                    task_priority=task_priority,
                )

    def exposed_get_all_completed_tasks(self) -> list[tuple[str, str, str, str]]:
        assert self.db_con is not None


        with DB_LOCK:
            with self.db_con:
                return get_all_completed_tasks(db_con=self.db_con)
            return []

    def exposed_set_task_processed(self, task_id: str) -> None:
        assert self.db_con is not None

        with DB_LOCK:
            with self.db_con:
                return set_task_processed(db_con=self.db_con, task_id=task_id)


class ControllerProxy:
    def __init__(self, host: str, port: int, key_file: str, cert_file: str, **kwargs):
        self.host = host
        self.port = port
        self.key_file = key_file
        self.cert_file = cert_file
        self.extra_kwargs = kwargs
        self.conn = robust_connect(
            host=self.host,
            port=self.port,
            key_file=self.key_file,
            cert_file=self.cert_file,
            **self.extra_kwargs,
        )

    def reconnect(self):
        self.conn.close()
        self.conn = robust_connect(
            host=self.host,
            port=self.port,
            key_file=self.key_file,
            cert_file=self.cert_file,
            **self.extra_kwargs,
        )

    def close(self):
        self.conn.close()

    # Setup distribution

    def add_setup(self, setup_name: str, setup_dir_tar: bytes) -> None:
        remote: Any = self.conn.root
        return remote.add_setup(setup_name=setup_name, setup_dir_tar=setup_dir_tar)

    def get_all_setup_names(self) -> list[str]:
        remote: Any = self.conn.root
        return remote.get_all_setup_names()

    def get_setup_dir_tar(self, setup_name: str) -> bytes:
        remote: Any = self.conn.root
        return remote.get_setup_dir_tar(setup_name=setup_name)

    # Agent - Controller Interaction

    def get_single_available_task(
        self, cluster: str
    ) -> Optional[tuple[str, str, str, int]]:
        remote: Any = self.conn.root
        return remote.get_single_available_task(cluster=cluster)

    def set_task_completed(self, task_id: str, task_result_json: str) -> None:
        remote: Any = self.conn.root
        return remote.set_task_completed(
            task_id=task_id, task_result_json=task_result_json
        )

    def set_task_failed(self, task_id: str) -> None:
        remote: Any = self.conn.root
        return remote.set_task_failed(
            task_id=task_id
        )

    # Task Source - Controller Interaction

    def add_new_task(
        self,
        task_id: str,
        task_type: str,
        task_data_json: str,
        task_priority: int,
    ) -> None:
        remote: Any = self.conn.root
        return remote.add_new_task(
            task_id=task_id,
            task_type=task_type,
            task_data_json=task_data_json,
            task_priority=task_priority,
        )

    def get_all_completed_tasks(self) -> list[tuple[str, str, str, str]]:
        remote: Any = self.conn.root
        return remote.get_all_completed_tasks()

    def set_task_processed(self, task_id: str) -> None:
        remote: Any = self.conn.root
        return remote.set_task_processed(task_id=task_id)


# End Main logic
# =============================================================================


def handle_exception(
    start_time: float,
    retry_time: float,
    inter_retry_time: float,
    err_type: str,
    exc_info: Optional[Exception],
) -> bool:
    # In case we have exhausted the retry time
    # log the exception and re raise
    now = time.monotonic()
    if now - start_time > retry_time:
        logger.error("%s: quitting=True", exc_info=exc_info)
        do_reraise = True
        return do_reraise

    # Otherwise just sleep and retry
    logger.warning("%s: retrying=True", err_type, exc_info=exc_info)
    time.sleep(inter_retry_time)
    do_reraise = False
    return do_reraise


def robust_connect(
    host: str, port: int, key_file: str, cert_file: str, **kwargs
) -> Connection:
    """Try to connect to the rpyc server; try to handle failures."""
    start_time = time.monotonic()
    do_handle_exception = partial(
        handle_exception, start_time, CONNECT_RETRY_TIME, CONNECT_INTER_RETRY_TIME
    )

    while True:
        try:
            # return rpyc.connect(*args, **kwargs)
            return rpyc.ssl_connect(
                host=host,
                port=port,
                keyfile=key_file,
                certfile=cert_file,
                ca_certs=cert_file,
                cert_reqs=ssl.CERT_REQUIRED,
                # We don't use PROTOCOL_TLS_CLIENT
                # as that sets check hostname which we don't care about.
                # We would like the same keyfiles to work
                # independent of where we start the server.
                ssl_version=ssl.PROTOCOL_TLS,
                **kwargs,
            )
        except ConnectionRefusedError:
            do_reraise = do_handle_exception(
                "failed-to-connect-to-server: connection-refused",
                exc_info=None,
            )
            if do_reraise:
                raise

        except ssl.SSLError as e:
            logger.error("failed-to-setup-ssl-connection: sslerror=%r", str(e))
            sys.exit(1)

        except Exception as e:
            do_reraise = do_handle_exception(
                "failed-to-connect-to-server: unexpected-exception",
                exc_info=e,
            )
            if do_reraise:
                raise


@click.command()
def controller():
    """Start the controller."""
    logger.info("getting controller config")
    config = get_controller_config()

    logger.info("initializing controller db")
    db_con_path = config.setup_root / "controller.db"
    db_con_path = str(db_con_path)
    db_con = apsw.Connection(db_con_path)
    db_con.execute("pragma busy_timeout=1800;")
    sdb.init_setup_db(db_con)
    tdb.init_task_db(db_con)
    db_con.close()

    authenticator = SSLAuthenticator(
        keyfile=config.key_file,
        certfile=config.cert_file,
        ca_certs=config.cert_file,
        cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
    )

    server = ThreadedServer(
        ControllerService,
        hostname=config.controller_host,
        port=config.controller_port,
        authenticator=authenticator,
    )

    logger.info("starting server")
    try:
        server.start()
    finally:
        server.close()
