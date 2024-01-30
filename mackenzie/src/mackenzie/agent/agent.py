"""Main Agent Logic."""

import shlex
import hashlib
import logging
from subprocess import run

import apsw

from ..db import setup_db as sdb
from ..controller.main import ControllerProxy
from .config import AgentConfig
from .slurm_pipeline import (
    process_failed,
    process_ready,
    process_running,
    process_new,
    SetupTaskType,
    GetTaskResultType,
)


logger = logging.getLogger(__name__)


def add_setup(
    config: AgentConfig,
    con: apsw.Connection,
    setup_name: str,
    setup_dir_tar: bytes,
) -> None:
    """Add a new set setup to the system."""
    logger.info("received add setup: setup_name=%s", setup_name)
    incoming_hash = hashlib.sha256(setup_dir_tar).hexdigest()

    setup_tar_file = config.setup_root / f"{setup_name}.tar.gz"
    if setup_tar_file.exists():
        logger.info("setup-tar-exists: setup_tar_file=%s", setup_tar_file)
        existing_hash = hashlib.sha256(setup_tar_file.read_bytes()).hexdigest()
        if existing_hash != incoming_hash:
            raise RuntimeError(
                f"Existing setup '{setup_name}' being replaced by a different setup."
            )
    else:
        logger.info("writing-setup-tar: setup_tar_file=%s", setup_tar_file)
        setup_tar_file.write_bytes(setup_dir_tar)

    setup_dir = config.setup_root / setup_name
    if not setup_dir.exists():
        logger.info("untarring-setup-tar: setup_tar_file=%s", setup_tar_file)
        cmd = f"tar -C '{config.setup_root}' -xzf '{setup_tar_file}'"
        logger.info("executing: %s", cmd)
        cmd = shlex.split(cmd)
        run(cmd, check=True)
        if not setup_dir.exists():
            raise RuntimeError(
                f"Untarring '{setup_tar_file!s}' did not create '{setup_dir}'"
            )

    try:
        sdb.add_new_setup(con, setup_name, incoming_hash)
    except apsw.ConstraintError:
        pass


def sync_setups(
    config: AgentConfig, controller: ControllerProxy, db_con: apsw.Connection
) -> None:
    """Ensure the agent has all the setups as the controller."""

    controller_setups = controller.get_all_setup_names()
    local_setups = sdb.get_all_setup_names(db_con)
    new_setups = set(controller_setups) - set(local_setups)
    if new_setups:
        for setup_name in new_setups:
            setup_dir_tar = controller.get_setup_dir_tar(setup_name)
            add_setup(config, db_con, setup_name, setup_dir_tar)


def process_jobs(
    con: apsw.Connection,
    config: AgentConfig,
    controller: ControllerProxy,
    type_setup_task: dict[str, SetupTaskType],
    type_get_task_result: dict[str, GetTaskResultType],
):
    """Process all tasks."""
    process_new(
        con=con,
        setup_root=config.setup_root,
        controller=controller,
        cluster=config.cluster,
        max_load=config.max_load,
        type_setup_task=type_setup_task,
    )

    process_running(
        con=con,
        setup_root=config.setup_root,
        controller=controller,
        type_get_task_result=type_get_task_result,
    )

    process_failed(
        con=con,
        setup_root=config.setup_root,
        controller=controller,
        type_setup_task=type_setup_task,
    )

    process_ready(con=con, max_load=config.max_load)
