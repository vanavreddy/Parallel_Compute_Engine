"""Slurm Pipeline."""

import os
import time
import shlex
import json
import subprocess
import logging
from pathlib import Path
from subprocess import run
from functools import partial
from typing import Callable, Optional, Any

import apsw

from ..db import job_db as jdb
from ..controller.main import ControllerProxy

SBATCH_EXE = os.environ.get("SBATCH_EXE", "sbatch")
SQUEUE_EXE = os.environ.get("SQUEUE_EXE", "squeue")
SACCT_EXE = os.environ.get("SACCT_EXE", "sacct")
USER = os.environ["USER"]

COMMAND_RETRY_TIME = 30 * 60
COMMAND_INTER_RETRY_TIME = 30
COMMAND_TIMEOUT = 300

MAX_FAILS = 100

SetupTaskType = Callable[[Path, Any], tuple[Path, int, int]]
GetTaskResultType = Callable[[Path, Any], Optional[dict[str, Any]]]

logger = logging.getLogger(__name__)


def log_called_process_error(e: subprocess.CalledProcessError) -> None:
    cmd_str = " ".join(e.cmd)
    logger.warning(
        "command_failed: cmd=%r returncode=%r\nstdout=%r\nstderr=%r",
        cmd_str,
        e.returncode,
        e.stdout,
        e.stderr,
    )


def handle_exception(
    start_time: float,
    err_type: str,
    exc_info: Optional[Exception],
) -> bool:
    # In case we have exhausted the retry time
    # log the exception and re raise
    now = time.monotonic()
    if now - start_time > COMMAND_RETRY_TIME:
        logger.error("%s: quitting=True", err_type, exc_info=exc_info)
        do_reraise = True
        return do_reraise

    # Otherwise just sleep and retry
    logger.warning("%s: retrying=True", err_type, exc_info=exc_info)
    time.sleep(COMMAND_INTER_RETRY_TIME)
    do_reraise = False
    return do_reraise


def do_get_running_jobids() -> set[int]:
    """Get the running slurm job ids."""
    cmd = f"{SQUEUE_EXE} -u {USER} --noheader -o %A"
    cmd = shlex.split(cmd)

    proc = run(cmd, capture_output=True, check=True, text=True, timeout=COMMAND_TIMEOUT)
    job_ids = proc.stdout.strip().split()
    job_ids = set(int(j) for j in job_ids)
    return job_ids


def get_running_jobids() -> set[int]:
    """Get the running slurm job ids; Tolerate failures."""
    start_time = time.monotonic()
    do_handle_exception = partial(handle_exception, start_time)
    while True:
        try:
            return do_get_running_jobids()
        except subprocess.CalledProcessError as e:
            log_called_process_error(e)

            do_reraise = do_handle_exception("squeue_failed", exc_info=None)
            if do_reraise:
                raise
        except Exception as e:
            do_reraise = do_handle_exception("squeue_failed", exc_info=e)
            if do_reraise:
                raise


def do_get_sacct_info(job_id: int) -> str:
    """Get the sacct info for a completed job."""
    cmd = f"{SACCT_EXE} -j {job_id} -o ALL -P"
    cmd = shlex.split(cmd)

    proc = run(cmd, capture_output=True, check=True, text=True, timeout=COMMAND_TIMEOUT)
    return proc.stdout


def get_sacct_info(job_id: int) -> str:
    """Get the sacct info for a completed job; Tolerate failures."""
    start_time = time.monotonic()
    do_handle_exception = partial(handle_exception, start_time)
    while True:
        try:
            return do_get_sacct_info(job_id)
        except subprocess.CalledProcessError as e:
            log_called_process_error(e)

            do_reraise = do_handle_exception("sacct_failed", exc_info=None)
            if do_reraise:
                raise
        except Exception as e:
            do_reraise = do_handle_exception("sacct_failed", exc_info=e)
            if do_reraise:
                raise


def do_submit_sbatch_job(sbatch_cmd_str: str, sbatch_env: dict[str, str]) -> int:
    """Submit a sbatch job."""
    cmd = shlex.split(sbatch_cmd_str)

    # We pick out the env vars we want to propagate during submitting.
    # This process maybe running within slurm.
    # We dont want the current process' slurm env vars to be propagated.

    env = {}
    for key in ["USER", "HOME", "PATH"]:
        env[key] = os.environ[key]
    for key, value in sbatch_env.items():
        env[key] = value

    proc = run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT,
        env=env,
    )
    job_id = proc.stdout.strip().split()[-1]
    job_id = int(job_id)
    return job_id


def submit_sbatch_job(sbatch_cmd_str: str, sbatch_env: dict[str, str] = {}) -> int:
    """Submit a sbatch job; Tolerate failures"""
    start_time = time.monotonic()
    do_handle_exception = partial(handle_exception, start_time)
    while True:
        try:
            return do_submit_sbatch_job(sbatch_cmd_str, sbatch_env)
        except subprocess.CalledProcessError as e:
            log_called_process_error(e)

            do_reraise = do_handle_exception("sbatch_failed", exc_info=None)
            if do_reraise:
                raise
        except Exception as e:
            do_reraise = do_handle_exception("sbatch_failed", exc_info=e)
            if do_reraise:
                raise


def process_running(
    con: apsw.Connection,
    setup_root: Path,
    controller: ControllerProxy,
    type_get_task_result: dict[str, GetTaskResultType],
) -> None:
    """Process the tasks that are running."""
    running_jobids = get_running_jobids()

    sql = """
        select job_id, job_type, job_data, slurm_job_id
        from job
        where job_state = 'running'
        """
    cur = con.execute(sql)

    cur_time = int(time.time())
    for job_id, job_type, job_data_json, slurm_job_id in cur:
        if slurm_job_id in running_jobids:
            continue

        sacct_info = get_sacct_info(slurm_job_id)
        jdb.set_slurm_job_completion_info(con, slurm_job_id, cur_time, sacct_info)

        job_data = json.loads(job_data_json)
        get_task_result = type_get_task_result[job_type]
        job_result = get_task_result(setup_root, job_data)
        if job_result is not None:
            job_result_json = json.dumps(job_result)
            controller.set_task_completed(
                task_id=job_id, task_result_json=job_result_json
            )
            jdb.set_job_completed(con, job_id, job_result_json)
            logger.info(
                "job completed: job_id=%r slurm_job_id=%r", job_id, slurm_job_id
            )
            continue

        jdb.set_job_failed(con, job_id)
        logger.warning("job failed: job_id=%r slurm_job_i=%r", job_id, slurm_job_id)


def process_failed(
    con: apsw.Connection,
    setup_root: Path,
    controller: ControllerProxy,
    type_setup_task: dict[str, SetupTaskType],
) -> None:
    """Process the tasks currently in failed state."""
    sql = """
        select job_id, job_type, job_data, failure_count, max_fails
        from job
        where job_state = 'failed'
        """
    cur = con.execute(sql)

    for job_id, job_type, job_data_json, failure_count, max_fails in cur:
        if failure_count > max_fails:
            controller.set_task_failed(task_id=job_id)
            jdb.set_job_aborted(con, job_id=job_id)
            logger.error(
                "job aborted: job_id=%r failure_count=%r", job_id, failure_count
            )
            continue

        job_data = json.loads(job_data_json)
        setup_task = type_setup_task[job_type]
        (
            sbatch_script_file,
            _,
            _,
        ) = setup_task(setup_root, job_data)
        jdb.set_job_ready(con=con, job_id=job_id, sbatch_script=str(sbatch_script_file))
        logger.info("job ready: job_id=%r failure_count=%r", job_id, failure_count)


def process_ready(con: apsw.Connection, max_load: int) -> None:
    """Process the tasks that are ready to be run."""
    cur_load = jdb.get_running_load(con)

    sql = """
        select job_id, sbatch_script, load
        from job
        where job_state = 'ready'
        order by job_priority desc, load desc, job_id asc
        """
    cur = con.execute(sql)

    for job_id, sbatch_script, load in cur:
        if cur_load + load > max_load:
            break

        cur_load = cur_load + load

        cmd = f"{SBATCH_EXE} {sbatch_script}"
        slurm_job_id = submit_sbatch_job(cmd)
        jdb.set_job_running(con, job_id, slurm_job_id)

        cur_time = int(time.time())
        jdb.add_slurm_job(con, slurm_job_id, job_id, cur_time)

        logger.info("job running: job_id=%r slurm_job_id=%r", job_id, slurm_job_id)


def process_new(
    con: apsw.Connection,
    setup_root: Path,
    controller: ControllerProxy,
    cluster: str,
    max_load: int,
    type_setup_task: dict[str, SetupTaskType],
) -> None:
    """Get and process new tasks from the controller."""
    cur_load = jdb.get_live_load(con)
    if cur_load >= max_load:
        return

    match controller.get_single_available_task(cluster):
        case None:
            return
        case (job_id, job_type, job_data_json, job_priority):
            job_data = json.loads(job_data_json)
            setup_task = type_setup_task[job_type]
            sbatch_script_file, load, max_fails = setup_task(setup_root, job_data)
            jdb.add_job(
                con=con,
                job_id=job_id,
                job_type=job_type,
                job_data=job_data_json,
                job_priority=job_priority,
                sbatch_script=str(sbatch_script_file),
                load=load,
                max_fails=max_fails,
            )
            logger.info("job ready: job_id=%r", job_id)
