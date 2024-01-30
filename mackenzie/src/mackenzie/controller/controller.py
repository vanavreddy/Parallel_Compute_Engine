"""Main Controller Logic."""

import time
import shlex
import hashlib
import logging
from subprocess import run
from typing import Optional

import apsw

from .config import ControllerConfig
from ..db import setup_db as sdb
from ..db import task_db as tdb

logger = logging.getLogger(__name__)

# Setup distribution
# ------------------


def add_setup(
    config: ControllerConfig,
    db_con: apsw.Connection,
    setup_name: str,
    setup_dir_tar: bytes,
) -> None:
    """Add a new set setup to the system."""
    logger.info("received add setup: setup_name=%s", setup_name)
    incoming_hash = hashlib.sha256(setup_dir_tar).hexdigest()

    setup_tar_file = config.setup_root / f"{setup_name}.tar.gz"
    if setup_tar_file.exists():
        logger.info("setup tar exists: setup_tar_file=%s", setup_tar_file)
        existing_hash = hashlib.sha256(setup_tar_file.read_bytes()).hexdigest()
        if existing_hash != incoming_hash:
            raise RuntimeError(
                f"Trying to replace existing setup '{setup_name}' with a different setup."
            )
    else:
        logger.info("writing setup tar: setup_tar_file=%s", setup_tar_file)
        setup_tar_file.write_bytes(setup_dir_tar)

    setup_dir = config.setup_root / setup_name
    if not setup_dir.exists():
        logger.info("untarring setup tar: setup_tar_file=%s", setup_tar_file)
        cmd = f"tar -C '{config.setup_root}' -xzf '{setup_tar_file}'"
        logger.info("executing: %s", cmd)
        cmd = shlex.split(cmd)
        run(cmd, check=True)
        if not setup_dir.exists():
            raise RuntimeError(
                f"Untarring '{setup_tar_file!s}' did not create '{setup_dir}'"
            )

    try:
        sdb.add_new_setup(db_con, setup_name, incoming_hash)
    except apsw.ConstraintError:
        pass


def get_all_setup_names(db_con: apsw.Connection) -> list[str]:
    """Get all registered setups."""
    return sdb.get_all_setup_names(db_con)


def get_setup_dir_tar(config: ControllerConfig, setup_name: str) -> bytes:
    """Get the setup dir tar."""
    setup_tar_file = config.setup_root / f"{setup_name}.tar.gz"
    if not setup_tar_file.exists():
        raise RuntimeError(f"Tar file for '{setup_name}' not found.")

    setup_dir_tar = setup_tar_file.read_bytes()
    return setup_dir_tar


# Agent - Controller Interaction
# ------------------------------


def make_timeout_tasks_available(
    config: ControllerConfig, db_con: apsw.Connection
) -> None:
    """Make the tasks that have reached timeout available again."""
    sql = """
        select task_id, assigned_at, assigned_to
        from task
        where task_state = 'assigned' and assigned_at < ?
        """

    start_time = int(time.time()) - config.task_timeout
    cur = db_con.execute(sql, (start_time,))
    for task_id, assigned_at, assigned_to in list(cur):
        logger.warning(
            "task timeout: task_id=%s, was_assinged_to=%s, was_assinged_at=%s",
            task_id,
            assigned_to,
            assigned_at,
        )

        tdb.set_task_available(con=db_con, task_id=task_id)


def get_single_available_task(
    config: ControllerConfig, db_con: apsw.Connection, cluster: str
) -> Optional[tuple[str, str, str, int]]:
    """Get one available task."""
    # Make the timed out tasks available again
    make_timeout_tasks_available(config=config, db_con=db_con)

    match tdb.get_single_available_task(con=db_con):
        case None:
            return None
        case (task_id, task_type, task_data_json, task_priority):
            logger.info("task assinged: task_id=%s, cluster=%s", task_id, cluster)
            now = int(time.time())
            tdb.set_task_assigned(
                con=db_con, task_id=task_id, assigned_to=cluster, assigned_at=now
            )
            return (task_id, task_type, task_data_json, task_priority)


def set_task_completed(
    db_con: apsw.Connection, task_id: str, task_result_json: str
) -> None:
    """Set the task to be completed."""
    logger.info("task completed: task_id=%s", task_id)
    tdb.set_task_completed(con=db_con, task_id=task_id, task_result=task_result_json)


def set_task_failed(db_con: apsw.Connection, task_id: str) -> None:
    """Set the task to be failed."""
    logger.info("task aborted: task_id=%s", task_id)
    tdb.set_task_failed(con=db_con, task_id=task_id)


# Task Source - Controller Interaction
# ------------------------------------


def add_new_task(
    db_con: apsw.Connection,
    task_id: str,
    task_type: str,
    task_data_json: str,
    task_priority: int,
) -> None:
    """Add a new task to the task database."""
    logger.info("adding new task: task_id=%s", task_id)
    tdb.add_new_task(
        con=db_con,
        task_id=task_id,
        task_type=task_type,
        task_data=task_data_json,
        task_priority=task_priority,
    )


def get_all_completed_tasks(db_con: apsw.Connection) -> list[tuple[str, str, str, str]]:
    """Get all completed tasks."""
    return tdb.get_all_completed_tasks(con=db_con)


def set_task_processed(db_con: apsw.Connection, task_id: str) -> None:
    """Mark task as processed."""
    logger.info("task processed: task_id=%s", task_id)
    tdb.set_task_processed(db_con, task_id)
