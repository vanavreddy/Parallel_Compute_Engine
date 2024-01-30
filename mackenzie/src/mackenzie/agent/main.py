"""Agent main entry point."""

import time
import logging

import apsw

from ..db import setup_db as sdb
from ..db import job_db as jdb
from ..controller.main import ControllerProxy
from .config import get_agent_config
from .agent import sync_setups, process_jobs
from .slurm_pipeline import SetupTaskType, GetTaskResultType

logger = logging.getLogger(__name__)


def agent_main(
    type_setup_task: dict[str, SetupTaskType],
    type_get_task_result: dict[str, GetTaskResultType],
):
    """Start the agent."""
    logger.info("getting agent config")
    config = get_agent_config()

    logger.info("conneting to controller")
    controller = ControllerProxy(
        host=config.controller_host,
        port=config.controller_port,
        key_file=str(config.key_file),
        cert_file=str(config.cert_file),
    )

    logger.info("initializing agent db")
    db_con_path = config.setup_root / "agent.db"
    db_con_path = str(db_con_path)
    db_con = apsw.Connection(db_con_path)
    db_con.execute("pragma busy_timeout=1800;")
    sdb.init_setup_db(db_con)
    jdb.init_job_db(db_con)

    while True:
        try:
            with db_con:
                sync_setups(config=config, controller=controller, db_con=db_con)
                process_jobs(
                    config=config,
                    con=db_con,
                    controller=controller,
                    type_setup_task=type_setup_task,
                    type_get_task_result=type_get_task_result,
                )
        except EOFError as e:
            logger.warning("connection dropped: reconnecting: %s", e)
            controller.reconnect()

        time.sleep(1)
