"""Slurm job database."""

from typing import cast

import apsw

from .db_common import UnexpectedCase


def init_job_db(con: apsw.Connection) -> None:
    """Initialize the job database."""
    sql = """
    create table if not exists job (
        job_id text primary key,
        job_type text,
        job_data text,
        job_priority text,

        sbatch_script text,
        load int,
        max_fails int,

        job_result text,

        slurm_job_id bigint,
        job_state text,
        failure_count int
    );

    create index if not exists job_state on job (job_state);

    create table if not exists slurm_job (
        slurm_job_id int primary key,
        job_id text,

        start_time bigint,
        end_time bigint,
        sacct_info text
    );

    create index if not exists slurm_job_job_id on slurm_job (job_id);
    """
    con.execute(sql)


def add_job(
    con: apsw.Connection,
    job_id: str,
    job_type: str,
    job_data: str,
    job_priority: int,
    sbatch_script: str,
    load: int,
    max_fails: int,
) -> None:
    sql = """
        insert into job values (
            ?,?,?,?,
            ?,?,?,
            null,
            null,'ready',0)
        """
    con.execute(
        sql,
        (job_id, job_type, job_data, job_priority, sbatch_script, load, max_fails),
    )


def set_job_ready(con: apsw.Connection, job_id: str, sbatch_script: str) -> None:
    sql = """
        update job
        set sbatch_script = ?, job_state = 'ready' 
        where job_id = ?
        """
    con.execute(sql, (sbatch_script, job_id))


def set_job_running(con: apsw.Connection, job_id: str, slurm_job_id: int) -> None:
    sql = """
        update job
        set job_state = 'running', slurm_job_id = ?
        where job_id = ?
        """
    con.execute(
        sql,
        (
            slurm_job_id,
            job_id,
        ),
    )


def set_job_failed(con: apsw.Connection, job_id: str) -> None:
    sql = """
        update job
        set job_state = 'failed', failure_count = failure_count + 1
        where job_id = ?
        """
    con.execute(sql, (job_id,))


def set_job_completed(con: apsw.Connection, job_id: str, job_result: str) -> None:
    sql = """
        update job
        set job_state = 'completed' and job_result = ?
        where job_id = ?
        """
    con.execute(sql, (job_result, job_id))


def set_job_processed(con: apsw.Connection, job_id: str) -> None:
    sql = """
        update job
        set job_state = 'processed'
        where job_id = ?
        """
    con.execute(sql, (job_id,))


def set_job_aborted(con: apsw.Connection, job_id: str) -> None:
    sql = """
        update job
        set job_state = 'aborted'
        where job_id = ?
        """
    con.execute(sql, (job_id,))


def add_slurm_job(
    con: apsw.Connection, slurm_job_id: int, job_id: str, start_time: int
) -> None:
    sql = "insert into slurm_job values (?,?, ?,null,null)"
    con.execute(sql, (slurm_job_id, job_id, start_time))


def set_slurm_job_completion_info(
    con: apsw.Connection, slurm_job_id: int, end_time: int, sacct_info: str
) -> None:
    sql = """
        update slurm_job
        set end_time = ? and sacct_info = ?
        where slurm_job_id = ?
        """
    con.execute(sql, (end_time, sacct_info, slurm_job_id))


def count_live_jobs(con: apsw.Connection) -> int:
    sql = """
        select count(*)
        from job
        where job_state in ('ready','running','failed')
        """
    cur = con.execute(sql)
    match cur.fetchall():
        case [[live_job_count]]:
            return cast(int, live_job_count)
        case other:
            raise UnexpectedCase(other)


def get_running_load(con: apsw.Connection) -> int:
    sql = """
        select sum(load)
        from job
        where job_state = 'running'
        """
    cur = con.execute(sql)
    match cur.fetchall():
        case [[None]]:
            return 0
        case [[system_load]]:
            return cast(int, system_load)
        case other:
            raise UnexpectedCase(other)


def get_live_load(con: apsw.Connection) -> int:
    sql = """
        select sum(load)
        from job
        where job_state in ('running', 'ready', 'failed')
        """
    cur = con.execute(sql)
    match cur.fetchall():
        case [[None]]:
            return 0
        case [[live_load]]:
            return cast(int, live_load)
        case other:
            raise UnexpectedCase(other)
