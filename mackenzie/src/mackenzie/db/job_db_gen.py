"""job_db

This module has been generated with SqlPyGen from job_db.sql.
"""

from dataclasses import dataclass
from typing import Optional, Iterable

import apsw

ConnectionType = apsw.Connection

SCHEMA = {}
SCHEMA[
    "job"
] = """
create table if not exists job (
    job_id text primary key,
    job_type text not null,
    job_data text not null,
    job_priority text not null,

    sbatch_script text not null,
    load int not null,
    max_fails int not null,

    job_result text,

    slurm_job_id bigint,
    job_state text not null,
    failure_count int not null
)
"""

SCHEMA[
    "job_state"
] = """
create index if not exists job_state on job (job_state)
"""

SCHEMA[
    "slurm_job"
] = """
create table if not exists slurm_job (
    slurm_job_id int primary key,
    job_id text not null,

    start_time bigint not null,
    end_time bigint,
    sacct_info text
)
"""

SCHEMA[
    "slurm_job_id"
] = """
create index if not exists slurm_job_job_id on slurm_job (job_id)
"""


QUERY = {}
QUERY[
    "add_job"
] = """
insert into job values (
    :job_id, :job_type, :job_data, :job_priority,
    :sbatch_script, :load, :max_fails,
    null,
    null, 'ready', 0
)
"""

QUERY[
    "set_job_ready"
] = """
update job
set sbatch_script = :sbatch_script, job_state = 'ready'
where job_id = :job_id
"""

QUERY[
    "set_job_running"
] = """
update job
set job_state = 'running', slurm_job_id = :slurm_job_id
where job_id = :job_id
"""

QUERY[
    "set_job_failed"
] = """
update job
set job_state = 'failed', failure_count = failure_count + 1
where job_id = :job_id
"""

QUERY[
    "set_job_completed"
] = """
update job
set job_state = 'completed' and job_result = :job_result
where job_id = :job_id
"""

QUERY[
    "set_job_processed"
] = """
update job
set job_state = 'processed'
where job_id = :job_id
"""

QUERY[
    "set_job_aborted"
] = """
update job
set job_state = 'aborted'
where job_id = :job_id
"""

QUERY[
    "add_slurm_job"
] = """
insert into slurm_job values (
    :slurm_job_id, :job_id, :start_time,
    null, null
)
"""

QUERY[
    "set_slurm_job_completion_info"
] = """
update slurm_job
set end_time = :end_time and sacct_info = :sacct_info
where slurm_job_id = :slurm_job_id
"""

QUERY[
    "count_live_jobs"
] = """
select count(*)
from job
where job_state in ('ready','running','failed')
"""

QUERY[
    "get_running_load"
] = """
select sum(load)
from job
where job_state = 'running'
"""

QUERY[
    "get_live_load"
] = """
select sum(load)
from job
where job_state in ('running', 'ready', 'failed')
"""

QUERY[
    "get_running_jobs"
] = """
select job_id, job_type, job_data, slurm_job_id
from job
where job_state = 'running'
"""

QUERY[
    "get_failed_jobs"
] = """
select job_id, job_type, job_data, failure_count, max_fails
from job
where job_state = 'failed'
"""

QUERY[
    "get_ready_jobs"
] = """
select job_id, sbatch_script, load
from job
where job_state = 'ready'
order by job_priority desc, load desc, job_id asc
"""


@dataclass
class CountLiveJobsReturnType:
    live_job_count: Optional[int]


@dataclass
class GetRunningLoadReturnType:
    running_load: Optional[int]


@dataclass
class GetLiveLoadReturnType:
    live_load: Optional[int]


@dataclass
class GetRunningJobsReturnType:
    job_id: str
    job_type: str
    job_data: str
    slurm_job_id: Optional[int]


@dataclass
class GetFailedJobsReturnType:
    job_id: str
    job_type: str
    job_data: str
    failure_count: int
    max_fails: int


@dataclass
class GetReadyJobsReturnType:
    job_id: str
    sbatch_script: str
    load: int


def create_schema(connection: ConnectionType) -> None:
    """Create the table schema."""
    with connection:
        cursor = connection.cursor()

        try:
            sql = SCHEMA["job"]

            cursor.execute(sql)
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred when creating schema: job"
            ) from e
        try:
            sql = SCHEMA["job_state"]

            cursor.execute(sql)
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred when creating schema: job_state"
            ) from e
        try:
            sql = SCHEMA["slurm_job"]

            cursor.execute(sql)
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred when creating schema: slurm_job"
            ) from e
        try:
            sql = SCHEMA["slurm_job_id"]

            cursor.execute(sql)
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred when creating schema: slurm_job_id"
            ) from e


def add_job(
    connection: ConnectionType,
    job_id: str,
    job_type: str,
    job_data: str,
    job_priority: int,
    sbatch_script: str,
    load: int,
    max_fails: int,
) -> None:
    """Query add_job."""
    cursor = connection.cursor()
    try:
        sql = QUERY["add_job"]

        query_args = {
            "job_id": job_id,
            "job_type": job_type,
            "job_data": job_data,
            "job_priority": job_priority,
            "sbatch_script": sbatch_script,
            "load": load,
            "max_fails": max_fails,
        }
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: add_job"
        ) from e


def set_job_ready(connection: ConnectionType, job_id: str, sbatch_script: str) -> None:
    """Query set_job_ready."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_job_ready"]

        query_args = {"job_id": job_id, "sbatch_script": sbatch_script}
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_job_ready"
        ) from e


def set_job_running(connection: ConnectionType, job_id: str, slurm_job_id: int) -> None:
    """Query set_job_running."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_job_running"]

        query_args = {"job_id": job_id, "slurm_job_id": slurm_job_id}
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_job_running"
        ) from e


def set_job_failed(connection: ConnectionType, job_id: str) -> None:
    """Query set_job_failed."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_job_failed"]

        query_args = {"job_id": job_id}
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_job_failed"
        ) from e


def set_job_completed(connection: ConnectionType, job_id: str, job_result: str) -> None:
    """Query set_job_completed."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_job_completed"]

        query_args = {"job_id": job_id, "job_result": job_result}
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_job_completed"
        ) from e


def set_job_processed(connection: ConnectionType, job_id: str) -> None:
    """Query set_job_processed."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_job_processed"]

        query_args = {"job_id": job_id}
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_job_processed"
        ) from e


def set_job_aborted(connection: ConnectionType, job_id: str) -> None:
    """Query set_job_aborted."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_job_aborted"]

        query_args = {"job_id": job_id}
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_job_aborted"
        ) from e


def add_slurm_job(
    connection: ConnectionType, slurm_job_id: int, job_id: int, start_time: int
) -> None:
    """Query add_slurm_job."""
    cursor = connection.cursor()
    try:
        sql = QUERY["add_slurm_job"]

        query_args = {
            "slurm_job_id": slurm_job_id,
            "job_id": job_id,
            "start_time": start_time,
        }
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: add_slurm_job"
        ) from e


def set_slurm_job_completion_info(
    connection: ConnectionType, slurm_job_id: int, end_time: int, sacct_info: str
) -> None:
    """Query set_slurm_job_completion_info."""
    cursor = connection.cursor()
    try:
        sql = QUERY["set_slurm_job_completion_info"]

        query_args = {
            "slurm_job_id": slurm_job_id,
            "end_time": end_time,
            "sacct_info": sacct_info,
        }
        cursor.execute(sql, query_args)

    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: set_slurm_job_completion_info"
        ) from e


def count_live_jobs(connection: ConnectionType) -> Optional[CountLiveJobsReturnType]:
    """Query count_live_jobs."""
    cursor = connection.cursor()
    try:
        sql = QUERY["count_live_jobs"]

        cursor.execute(sql)

        row = cursor.fetchone()
        if row is None:
            return None
        else:
            return CountLiveJobsReturnType(live_job_count=row[0])
    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: count_live_jobs"
        ) from e


def get_running_load(connection: ConnectionType) -> Optional[GetRunningLoadReturnType]:
    """Query get_running_load."""
    cursor = connection.cursor()
    try:
        sql = QUERY["get_running_load"]

        cursor.execute(sql)

        row = cursor.fetchone()
        if row is None:
            return None
        else:
            return GetRunningLoadReturnType(running_load=row[0])
    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: get_running_load"
        ) from e


def get_live_load(connection: ConnectionType) -> Optional[GetLiveLoadReturnType]:
    """Query get_live_load."""
    cursor = connection.cursor()
    try:
        sql = QUERY["get_live_load"]

        cursor.execute(sql)

        row = cursor.fetchone()
        if row is None:
            return None
        else:
            return GetLiveLoadReturnType(live_load=row[0])
    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: get_live_load"
        ) from e


def get_running_jobs(connection: ConnectionType) -> Iterable[GetRunningJobsReturnType]:
    """Query get_running_jobs."""
    cursor = connection.cursor()
    try:
        sql = QUERY["get_running_jobs"]

        cursor.execute(sql)

        for row in cursor:
            row = GetRunningJobsReturnType(
                job_id=row[0], job_type=row[1], job_data=row[2], slurm_job_id=row[3]
            )
            yield row
    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: get_running_jobs"
        ) from e


def get_failed_jobs(connection: ConnectionType) -> Iterable[GetFailedJobsReturnType]:
    """Query get_failed_jobs."""
    cursor = connection.cursor()
    try:
        sql = QUERY["get_failed_jobs"]

        cursor.execute(sql)

        for row in cursor:
            row = GetFailedJobsReturnType(
                job_id=row[0],
                job_type=row[1],
                job_data=row[2],
                failure_count=row[3],
                max_fails=row[4],
            )
            yield row
    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: get_failed_jobs"
        ) from e


def get_ready_jobs(connection: ConnectionType) -> Iterable[GetReadyJobsReturnType]:
    """Query get_ready_jobs."""
    cursor = connection.cursor()
    try:
        sql = QUERY["get_ready_jobs"]

        cursor.execute(sql)

        for row in cursor:
            row = GetReadyJobsReturnType(
                job_id=row[0], sbatch_script=row[1], load=row[2]
            )
            yield row
    except Exception as e:
        raise RuntimeError(
            "An unexpected exception occurred while executing query: get_ready_jobs"
        ) from e


def explain_queries() -> None:
    connection = apsw.Connection(":memory:")
    create_schema(connection)

    with connection:
        cursor = connection.cursor()

        try:
            sql = QUERY["add_job"]
            sql = "EXPLAIN " + sql

            query_args = {
                "job_id": None,
                "job_type": None,
                "job_data": None,
                "job_priority": None,
                "sbatch_script": None,
                "load": None,
                "max_fails": None,
            }
            cursor.execute(sql, query_args)

            print("Query add_job is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: add_job"
            ) from e

        try:
            sql = QUERY["set_job_ready"]
            sql = "EXPLAIN " + sql

            query_args = {"job_id": None, "sbatch_script": None}
            cursor.execute(sql, query_args)

            print("Query set_job_ready is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_job_ready"
            ) from e

        try:
            sql = QUERY["set_job_running"]
            sql = "EXPLAIN " + sql

            query_args = {"job_id": None, "slurm_job_id": None}
            cursor.execute(sql, query_args)

            print("Query set_job_running is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_job_running"
            ) from e

        try:
            sql = QUERY["set_job_failed"]
            sql = "EXPLAIN " + sql

            query_args = {"job_id": None}
            cursor.execute(sql, query_args)

            print("Query set_job_failed is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_job_failed"
            ) from e

        try:
            sql = QUERY["set_job_completed"]
            sql = "EXPLAIN " + sql

            query_args = {"job_id": None, "job_result": None}
            cursor.execute(sql, query_args)

            print("Query set_job_completed is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_job_completed"
            ) from e

        try:
            sql = QUERY["set_job_processed"]
            sql = "EXPLAIN " + sql

            query_args = {"job_id": None}
            cursor.execute(sql, query_args)

            print("Query set_job_processed is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_job_processed"
            ) from e

        try:
            sql = QUERY["set_job_aborted"]
            sql = "EXPLAIN " + sql

            query_args = {"job_id": None}
            cursor.execute(sql, query_args)

            print("Query set_job_aborted is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_job_aborted"
            ) from e

        try:
            sql = QUERY["add_slurm_job"]
            sql = "EXPLAIN " + sql

            query_args = {"slurm_job_id": None, "job_id": None, "start_time": None}
            cursor.execute(sql, query_args)

            print("Query add_slurm_job is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: add_slurm_job"
            ) from e

        try:
            sql = QUERY["set_slurm_job_completion_info"]
            sql = "EXPLAIN " + sql

            query_args = {"slurm_job_id": None, "end_time": None, "sacct_info": None}
            cursor.execute(sql, query_args)

            print("Query set_slurm_job_completion_info is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: set_slurm_job_completion_info"
            ) from e

        try:
            sql = QUERY["count_live_jobs"]
            sql = "EXPLAIN " + sql

            cursor.execute(sql)

            print("Query count_live_jobs is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: count_live_jobs"
            ) from e

        try:
            sql = QUERY["get_running_load"]
            sql = "EXPLAIN " + sql

            cursor.execute(sql)

            print("Query get_running_load is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: get_running_load"
            ) from e

        try:
            sql = QUERY["get_live_load"]
            sql = "EXPLAIN " + sql

            cursor.execute(sql)

            print("Query get_live_load is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: get_live_load"
            ) from e

        try:
            sql = QUERY["get_running_jobs"]
            sql = "EXPLAIN " + sql

            cursor.execute(sql)

            print("Query get_running_jobs is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: get_running_jobs"
            ) from e

        try:
            sql = QUERY["get_failed_jobs"]
            sql = "EXPLAIN " + sql

            cursor.execute(sql)

            print("Query get_failed_jobs is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: get_failed_jobs"
            ) from e

        try:
            sql = QUERY["get_ready_jobs"]
            sql = "EXPLAIN " + sql

            cursor.execute(sql)

            print("Query get_ready_jobs is syntactically valid.")
        except Exception as e:
            raise RuntimeError(
                "An unexpected exception occurred while executing query plan for: get_ready_jobs"
            ) from e


if __name__ == "__main__":
    explain_queries()
