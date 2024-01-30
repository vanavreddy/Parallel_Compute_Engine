"""Setup database."""

from typing import Optional, cast
import apsw

from .db_common import UnexpectedCase


def init_setup_db(con: apsw.Connection) -> None:
    sql = """
    create table if not exists setup (
        setup_name text primary key,
        setup_hash text
    );

    create index if not exists setup_hash on setup (setup_hash);
    """

    con.execute(sql)


def add_new_setup(con: apsw.Connection, setup_name: str, setup_hash: str):
    sql = "insert into setup values (?, ?)"
    con.execute(sql, (setup_name, setup_hash))


def get_all_setup_names(con: apsw.Connection) -> list[str]:
    sql = "select setup_name from setup"
    cur = con.execute(sql)
    setup_names = [n for n, in cur]
    return setup_names


def get_setup_hash(con: apsw.Connection, setup_name: str) -> Optional[str]:
    sql = """
    select setup_hash
    from setup
    where setup_name = ?
    """
    cur = con.execute(sql, (setup_name,))
    match cur.fetchall():
        case [[setup_hash]]:
            return cast(str, setup_hash)
        case None:
            return None
        case other:
            raise UnexpectedCase(other)
