"""Task database."""

from typing import Optional, cast

import apsw

from .db_common import UnexpectedCase


def init_task_db(con: apsw.Connection) -> None:
    sql = """
    create table if not exists task (
        task_id text primary key,
        task_type text,
        task_data text,
        task_priority int,

        task_result text,
        
        task_state text,
        assigned_to text,
        assigned_at bigint
    );

    create index if not exists task_state on task (task_state);
    """

    con.execute(sql)


def add_new_task(
    con: apsw.Connection,
    task_id: str,
    task_type: str,
    task_data: str,
    task_priority: int,
) -> None:
    sql = """
        insert into task values (
            ?,?,?,?,
            null,
            'available',null,null
        )
        """
    con.execute(
        sql,
        (task_id, task_type, task_data, task_priority),
    )


def set_task_available(con: apsw.Connection, task_id: str) -> None:
    sql = """
        update task
        set task_state = 'available', assigned_to = null, assigned_at = null
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def set_task_assigned(
    con: apsw.Connection, task_id: str, assigned_to: str, assigned_at: int
) -> None:
    sql = """
        update task
        set task_state = 'assigned', assigned_to = ?, assigned_at = ?
        where task_id = ?
        """
    con.execute(sql, (assigned_to, assigned_at, task_id))


def set_task_completed(con: apsw.Connection, task_id: str, task_result: str) -> None:
    sql = """
        update task
        set task_state = 'completed', task_result = ?
        where task_id = ?
        """
    con.execute(sql, (task_result, task_id))


def set_task_failed(con: apsw.Connection, task_id: str) -> None:
    sql = """
        update task
        set task_state = 'failed'
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def set_task_processed(con: apsw.Connection, task_id: str) -> None:
    sql = """
        update task
        set task_state = 'processed'
        where task_id = ?
        """
    con.execute(sql, (task_id,))


def get_single_available_task(
    con: apsw.Connection,
) -> Optional[tuple[str, str, str, int]]:
    sql = """
        select task_id, task_type, task_data, task_priority
        from task
        where task_state = 'available'
        order by task_priority desc
        limit 1
        """
    cur = con.execute(sql)
    match cur.fetchall():
        case [[task_id, task_type, task_data, task_priority]]:
            task_id = cast(str, task_id)
            task_type = cast(str, task_type)
            task_data = cast(str, task_data)
            task_priority = cast(int, task_priority)
            return (task_id, task_type, task_data, task_priority)
        case []:
            return None
        case other:
            raise UnexpectedCase(other)


def get_all_completed_tasks(
    con: apsw.Connection,
) -> list[tuple[str, str, str, str]]:
    sql = """
        select task_id, task_type, task_data, task_result
        from task
        where task_state = 'completed'
        """
    cur = con.execute(sql)
    ret = []
    for (task_id, task_type, task_data, task_result) in cur:
        task_id = cast(str, task_id)
        task_type = cast(str, task_type)
        task_data = cast(str, task_data)
        task_result = cast(str, task_result)
        ret.append((task_id, task_type, task_data, task_result))
    return ret
