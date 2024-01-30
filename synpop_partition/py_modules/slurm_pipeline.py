"""Slurm Pipeline."""

import os
import time
import shlex
import json
import sqlite3
import logging
import subprocess
from pathlib import Path
from subprocess import run
from typing import Callable, Any


SQUEUE_EXE = os.environ.get("SQUEUE_EXE", "squeue")
USER = os.environ["USER"]

SQUEUE_RETRY_TIME = 30 * 60
SQUEUE_INTER_RETRY_TIME = 30
SQUEUE_TIMEOUT = 300

SBATCH_RETRY_TIME = 30 * 60
SBATCH_INTER_RETRY_TIME = 30
SBATCH_TIMEOUT = 300

MAX_FAILS = 100

log = logging.getLogger(__name__)


def log_called_process_error(e: subprocess.CalledProcessError) -> None:
    cmd_str = " ".join(e.cmd)
    msg = "Command failed: %s\nreturncode: %s\nstdout: %s\nstderr: %s"
    log.warning(msg, cmd_str, e.returncode, e.stdout, e.stderr)


def handle_exception(
    start_time: float,
    retry_time: float,
    inter_retry_time: float,
    error_desc: str,
    exc_info: bool,
) -> bool:
    # In case we have exhausted the retry time
    # log the exception and re raise
    now = time.monotonic()
    if now - start_time > retry_time:
        log.error("%s; quitting", error_desc, exc_info=exc_info)
        do_reraise = True
        return do_reraise

    # Otherwise just sleep and retry
    log.warning("%s; retrying", error_desc, exc_info=exc_info)
    time.sleep(inter_retry_time)
    do_reraise = False
    return do_reraise


def do_get_running_jobids() -> set[int]:
    """Get the running slurm job ids."""
    cmd = f"{SQUEUE_EXE} -u {USER} --noheader -o %A"
    cmd = shlex.split(cmd)

    proc = run(cmd, capture_output=True, check=True, text=True, timeout=SQUEUE_TIMEOUT)
    job_ids = proc.stdout.strip().split()
    job_ids = set(int(j) for j in job_ids)
    return job_ids


def get_running_jobids() -> set[int]:
    """Get the running slurm job ids; Tolerate failures."""
    start_time = time.monotonic()
    while True:
        try:
            return do_get_running_jobids()
        except subprocess.CalledProcessError as e:
            log_called_process_error(e)

            error_desc = "Failed to get output of squeue"
            do_reraise = handle_exception(
                start_time,
                SQUEUE_RETRY_TIME,
                SQUEUE_INTER_RETRY_TIME,
                error_desc,
                exc_info=False,
            )
            if do_reraise:
                raise
        except Exception:
            error_desc = "Failed to get output of squeue"
            do_reraise = handle_exception(
                start_time,
                SQUEUE_RETRY_TIME,
                SQUEUE_INTER_RETRY_TIME,
                error_desc,
                exc_info=True,
            )
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
        cmd, check=True, capture_output=True, text=True, timeout=SBATCH_TIMEOUT, env=env
    )
    job_id = proc.stdout.strip().split()[-1]
    job_id = int(job_id)
    return job_id


def submit_sbatch_job(sbatch_cmd_str: str, sbatch_env: dict[str, str]) -> int:
    """Submit a sbatch job; Tolerate failures"""
    start_time = time.monotonic()
    while True:
        try:
            return do_submit_sbatch_job(sbatch_cmd_str, sbatch_env)
        except subprocess.CalledProcessError as e:
            log_called_process_error(e)

            error_desc = "Failed to submit sbatch job"
            do_reraise = handle_exception(
                start_time,
                SBATCH_RETRY_TIME,
                SQUEUE_INTER_RETRY_TIME,
                error_desc,
                exc_info=False,
            )
            if do_reraise:
                raise
        except Exception as e:
            error_desc = "Failed to submit sbatch job"
            do_reraise = handle_exception(
                start_time,
                SBATCH_RETRY_TIME,
                SQUEUE_INTER_RETRY_TIME,
                error_desc,
                exc_info=True,
            )
            if do_reraise:
                raise


def init_task_db(con: sqlite3.Connection) -> None:
    """Initialize the task database."""
    sql = """
    create table if not exists task (
        task_id text primary key,
        task_meta text,

        sbatch_cmd text,
        sbatch_env text,
        output_dir text,

        load int,
        priority int,
        max_fails int,

        slurm_job_id bigint,
        state text,
        failure_count int
    );

    create index if not exists task_state on task (state);
    """
    con.executescript(sql)


def add_task(
    con: sqlite3.Connection,
    task_id: str,
    task_meta: Any,
    sbatch_cmd: str,
    sbatch_env: dict[str, Any],
    output_dir: str | Path,
    load: int,
    priority: int,
    max_fails: int,
) -> None:
    """Add a task to the task database."""
    task_meta_json = json.dumps(task_meta, default=str)
    sbatch_cmd = " ".join(shlex.split(sbatch_cmd))

    sbatch_env = {k: str(v) for k, v in sbatch_env.items()}
    sbatch_env_json = json.dumps(sbatch_env)

    output_dir = str(output_dir)

    sql = "insert into task values (?,?, ?,?,?, ?,?,?, null,'ready',0)"
    con.execute(
        sql,
        (
            task_id,
            task_meta_json,
            sbatch_cmd,
            sbatch_env_json,
            output_dir,
            load,
            priority,
            max_fails,
        ),
    )


def set_task_ready(con: sqlite3.Connection, task_id: str) -> None:
    sql = """
        update task
        set state = 'ready'
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def set_task_running(con: sqlite3.Connection, task_id: str, slurm_job_id: int) -> None:
    sql = """
        update task
        set state = 'running', slurm_job_id = ?
        where task_id = ?
        """
    con.execute(
        sql,
        (
            slurm_job_id,
            task_id,
        ),
    )


def set_task_failed(con: sqlite3.Connection, task_id: str) -> None:
    sql = """
        update task
        set state = 'failed', failure_count = failure_count + 1
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def set_task_completed(con: sqlite3.Connection, task_id: str) -> None:
    sql = """
        update task
        set state = 'completed'
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def set_task_processed(con: sqlite3.Connection, task_id: str) -> None:
    sql = """
        update task
        set state = 'processed'
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def set_task_aborted(con: sqlite3.Connection, task_id: str) -> None:
    sql = """
        update task
        set state = 'aborted'
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def count_live_tasks(con: sqlite3.Connection) -> int:
    sql = """
        select count(*)
        from task
        where state in ('ready','running','failed')
        """
    (count,) = con.execute(sql).fetchone()
    return count


def get_system_load(con: sqlite3.Connection) -> int:
    sql = """
        select sum(load)
        from task
        where state = 'running'
        """
    (cur_load,) = con.execute(sql).fetchone()
    if cur_load is None:
        cur_load = 0

    return cur_load


def process_running(
    con: sqlite3.Connection,
    check_job_successful: Callable[[str, Any], bool],
) -> None:
    """Process the tasks that are running."""
    running_jobids = get_running_jobids()

    sql = """
        select task_id, task_meta, slurm_job_id
        from task
        where state = 'running'
        """
    cur = con.execute(sql)

    for task_id, task_meta_json, slurm_job_id in cur:
        if slurm_job_id in running_jobids:
            continue

        task_meta = json.loads(task_meta_json)
        if check_job_successful(task_id, task_meta):
            set_task_completed(con, task_id)
            log.info(
                "Task completed: task_id = %s, slurm_job_id = %d",
                task_id,
                slurm_job_id,
            )
            continue

        set_task_failed(con, task_id)
        log.warning(
            "Task failed: task_id = %s, slurm_job_id = %d",
            task_id,
            slurm_job_id,
        )


def process_failed(
    con: sqlite3.Connection,
) -> None:
    """Process the tasks currently in failed state."""
    sql = """
        select task_id, failure_count, max_fails
        from task
        where state = 'failed'
        """
    cur = con.execute(sql)

    for task_id, failure_count, max_fails in cur:
        if failure_count > max_fails:
            set_task_aborted(con, task_id)
            log.error(
                "Task aborted: task_id = %s failure_count = %d",
                task_id,
                failure_count,
            )
            continue

        set_task_ready(con, task_id)
        log.info(
            "Task ready: task_id = %s, failure_count = %d",
            task_id,
            failure_count,
        )


def mkdir_output_dir(output_dir: Path) -> None:
    """Create a fresh output directory.

    If the directory already exists rename it with -fail-{i} suffix,
    and create a fresh output directory.
    """
    if output_dir.exists():
        for i in range(1, MAX_FAILS + 1):
            fail_dir = str(output_dir) + f"-fail_{i}"
            fail_dir = Path(fail_dir)
            if fail_dir.exists():
                continue

            output_dir.replace(fail_dir)
            break

    output_dir.mkdir(mode=0o770, parents=True, exist_ok=False)


def process_ready(con: sqlite3.Connection, max_load: int) -> None:
    """Process the tasks that are ready to be run."""
    cur_load = get_system_load(con)

    sql = """
        select task_id, sbatch_cmd, sbatch_env, output_dir, load
        from task
        where state = 'ready'
        order by priority desc, load desc, task_id asc
        """
    cur = con.execute(sql)

    for task_id, sbatch_cmd, sbatch_env_json, output_dir_str, load in cur:
        if cur_load + load > max_load:
            break

        cur_load = cur_load + load
        sbatch_env = json.loads(sbatch_env_json)

        output_dir = Path(output_dir_str)
        mkdir_output_dir(output_dir)

        set_task_running(con, task_id, -1)
        slurm_job_id = submit_sbatch_job(sbatch_cmd, sbatch_env)
        set_task_running(con, task_id, slurm_job_id)
        log.info(
            "Task running: task_id = %s, slurm_job_id = %d",
            task_id,
            slurm_job_id,
        )
