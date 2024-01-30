"""Save and load minimizer from a sqlite3 database."""

from typing import Optional, cast

import apsw


class UnexpectedCase(RuntimeError):
    def __init__(self, other):
        super().__init__("Unexpected case: %r" % other)


def init_minimizer_db(con: apsw.Connection) -> None:
    """Initialize the minimizer cache database."""
    sql = """
    create table if not exists minimizer_state (
        min_id text primary key,
        min_state text,
        min_type text,
        min_context text
    );
    """
    con.execute(sql)


def add_minimizer(
    con: apsw.Connection, min_id: str, min_state: str, min_type: str, min_context: str
) -> None:
    """Add a minimizer to the db."""
    sql = "insert into minimizer_state values (?,?,?,?)"
    con.execute(sql, (min_id, min_state, min_type, min_context))


def update_minimizer(con: apsw.Connection, min_id: str, min_state: str) -> None:
    """Update the state of an existing minimzer in db."""
    sql = """
        update minimizer_state
        set min_state = ?
        where min_id = ?
        """
    con.execute(sql, (min_state, min_id))


def get_minimizer(con: apsw.Connection, min_id: str) -> Optional[tuple[str, str]]:
    """Load the minimizer from db."""
    sql = """
        select min_state, min_context
        from minimizer_state
        where min_id = ?
        """
    cur = con.execute(sql, (min_id,))
    match cur.fetchall():
        case []:
            return None
        case [[min_state, min_context]]:
            min_state = cast(str, min_state)
            min_context = cast(str, min_context)
            return (min_state, min_context)
        case other:
            raise UnexpectedCase(other)


def get_all_minimizers(
    con: apsw.Connection,
) -> list[tuple[str, str, str, str]]:
    """Load all minimizers from db."""
    sql = """
        select min_id, min_state, min_type, min_context
        from minimizer_state
        """
    cur = con.execute(sql)
    return list(cur)
