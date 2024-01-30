"""Minimize a scalar."""

import json
import math
import logging
import sqlite3
from typing import Any, Optional

import pandas as pd
from scipy.optimize import minimize_scalar

log = logging.getLogger(__name__)

EPSILON = 1e-9


class _UnknownEvaluation(Exception):
    """Unknown evaluation."""

    def __init__(self, x: float):
        """Initialize."""
        super().__init__()
        self.x = x


class MinimzationSuccess(Exception):
    """Minimzation successful."""

    def __init__(self, x: float, y: float):
        super().__init__()
        self.x = x
        self.y = y


class MinimzationFailed(Exception):
    """Minimzation failed."""

    def __init__(self, x: float, y: float):
        super().__init__()
        self.x = x
        self.y = y


class ManualScalarMinimizer:
    """Manually minimize a scalar function."""

    def __init__(
        self,
        min_x: float = 0.0,
        max_x: float = 1.0,
        target_y: float = 1.0,
        tol: float = 0.01,
        max_evals: int = 100,
    ):
        self.min_x = min_x
        self.max_x = max_x
        self.target_y = target_y
        self.tol = tol
        self.max_evals = max_evals

        self.eval_cache: list[tuple[float, float]] = []

    def state_dict(self) -> dict[str, Any]:
        """Return a copy of the state dict."""
        d = dict(self.__dict__)
        d["eval_cache"] = list(d["eval_cache"])
        return d

    def load_state_dict(self, d: dict[str, Any]) -> None:
        """Load the state from a saved dict."""
        for k in self.__dict__:
            self.__dict__[k] = d[k]
        self.__dict__["eval_cache"] = list(self.__dict__["eval_cache"])

    @staticmethod
    def _round(x: float) -> float:
        return round(x, 6)

    def _fun(self, x: float) -> float:
        x = self._round(x)
        ecache = dict(self.eval_cache)
        if x in ecache:
            ret = (ecache[x] - self.target_y) ** 2
            return ret

        raise _UnknownEvaluation(x)

    def current_best(self) -> tuple[float, float, bool]:
        """Return best_x, best_y, is_optimal."""
        if not self.eval_cache:
            NAN = float("nan")
            return (NAN, NAN, False)

        xs = []
        for x, y in self.eval_cache:
            abs_err = abs(y - self.target_y)
            xs.append((abs_err, x, y))
        xs.sort()
        best_err, best_x, best_y = xs[0]

        if best_err <= self.target_y * self.tol:
            is_optimal = True
        else:
            is_optimal = False

        return best_x, best_y, is_optimal

    def update_min_max(self) -> None:
        """Update the min_x, max_x bounds to best known."""
        min_x = [x for x, y in self.eval_cache if y < self.target_y]
        min_x = min_x + [self.min_x]
        self.min_x = max(min_x)

        max_x = [x for x, y in self.eval_cache if y > self.target_y]
        max_x = max_x + [self.max_x]
        self.max_x = min(max_x)

    def do_run_minimizer(self):
        # We assume the function is monotonic
        # In case min_x > max_x this assumption is violated
        # We simply log the issue and terminate the optimization
        if self.min_x > self.max_x:
            log.warning(
                "Monotonicity assumption violated; min_x (%f) > max_x (%f); target_y = %f",
                self.min_x,
                self.max_x,
                self.target_y,
            )
            x = (self.min_x + self.max_x) / 2
            y = self.target_y
            self.set_y(x, y)
            return

        # Run the minimizer
        kwargs = {
            "bounds": (self.min_x, self.max_x),
            "options": {"maxiter": self.max_evals},
            "method": "bounded",
        }
        minimize_scalar(self._fun, **kwargs)

    def next_x(self) -> float:
        """Get the next x to test."""
        best_x, best_y, is_optimal = self.current_best()
        if is_optimal:
            raise MinimzationSuccess(best_x, best_y)

        if len(self.eval_cache) >= self.max_evals:
            raise MinimzationFailed(best_x, best_y)

        try:
            self.do_run_minimizer()
            best_x, best_y, is_optimal = self.current_best()
            if is_optimal:
                raise MinimzationSuccess(best_x, best_y)

            self.update_min_max()

            self.do_run_minimizer()
            best_x, best_y, is_optimal = self.current_best()
            if is_optimal:
                raise MinimzationSuccess(best_x, best_y)
            else:
                raise MinimzationFailed(best_x, best_y)
        except _UnknownEvaluation as e:
            return e.x

    def set_y(self, x: float, y: float) -> None:
        """Set the function evaluation value."""
        x = self._round(x)
        self.eval_cache.append((x, y))


class ManualErrorMinimizer:
    """Manually minimize an error function."""

    def __init__(
        self,
        min_x: float = 0.0,
        max_x: float = 1.0,
        min_evals: int = 5,
        max_evals: int = 100,
        last_k: int = 3,
        min_last_k_improvement: float = 0.1,
        target_y: float = 0.0,
    ):
        assert max_evals > min_evals
        assert last_k < min_evals

        self.min_x = min_x
        self.max_x = max_x
        self.min_evals = min_evals
        self.max_evals = max_evals
        self.last_k = last_k
        self.min_last_k_improvement = min_last_k_improvement

        # Interface compatibility with ManualScalarMinimizer
        self.target_y = target_y

        self.eval_cache: list[tuple[float, float]] = []

    def state_dict(self) -> dict[str, Any]:
        """Return a copy of the state dict."""
        d = dict(self.__dict__)
        d["eval_cache"] = list(d["eval_cache"])
        return d

    def load_state_dict(self, d: dict[str, Any]) -> None:
        """Load the state from a saved dict."""
        for k in self.__dict__:
            self.__dict__[k] = d[k]
        self.__dict__["eval_cache"] = list(self.__dict__["eval_cache"])

    @staticmethod
    def _round(x: float) -> float:
        return round(x, 6)

    def _fun(self, x: float) -> float:
        x = self._round(x)
        ecache = dict(self.eval_cache)
        if x in ecache:
            return ecache[x]

        raise _UnknownEvaluation(x)

    def should_stop(self) -> bool:
        if len(self.eval_cache) >= self.max_evals:
            return True
        if len(self.eval_cache) < self.min_evals:
            return False

        best = min(err for _, err in self.eval_cache)
        if math.isclose(best, self.target_y):
            return True

        prev_ec = self.eval_cache[: -self.last_k]
        prev_best = min(err for _, err in prev_ec)

        cur_ec = self.eval_cache[-self.last_k :]
        cur_best = min(err for _, err in cur_ec)

        improvement = abs(prev_best - cur_best) / abs(prev_best + EPSILON)
        if improvement < self.min_last_k_improvement:
            return True

        return False

    def current_best(self) -> tuple[float, float, bool]:
        """Return best_x, best_err, should_stop."""
        if not self.eval_cache:
            NAN = float("nan")
            return (NAN, NAN, False)

        xs = sorted(self.eval_cache, key=lambda x: x[1])
        best_x, best_err = xs[0]

        is_optimal = self.should_stop()

        return best_x, best_err, is_optimal

    def do_run_minimizer(self):
        # Run the minimizer
        kwargs = {
            "bounds": (self.min_x, self.max_x),
            "options": {"maxiter": self.max_evals},
            "method": "bounded",
        }
        minimize_scalar(self._fun, **kwargs)

    def next_x(self) -> float:
        """Get the next x to test."""
        best_x, best_err, is_optimal = self.current_best()
        if is_optimal:
            raise MinimzationSuccess(best_x, best_err)

        try:
            self.do_run_minimizer()

            best_x, best_err, is_optimal = self.current_best()

            #assert is_optimal
            raise MinimzationSuccess(best_x, best_err)
        except _UnknownEvaluation as e:
            return e.x

    def set_y(self, x: float, y: float) -> None:
        """Set the function evaluation value."""
        y = abs(y)

        x = self._round(x)
        self.eval_cache.append((x, y))


ManualMinimizer = ManualScalarMinimizer | ManualErrorMinimizer
ManualMinimizerType = type[ManualMinimizer]


def init_minimizer_db(con: sqlite3.Connection) -> None:
    """Initialize the minimizer cache database."""
    sql = """
    create table if not exists minimizer_state (
        grp text primary key,
        state_dict text
    );
    """
    con.executescript(sql)


def add_minimizer(con: sqlite3.Connection, group: str, msm: ManualMinimizer) -> None:
    """Add a minimizer to the db."""
    state_dict = msm.state_dict()
    state_dict_json = json.dumps(state_dict)

    sql = "insert into minimizer_state values (?,?)"
    con.execute(sql, (group, state_dict_json))


def update_minimizer(con: sqlite3.Connection, group: str, msm: ManualMinimizer) -> None:
    """Update the state of an existing minimzer in db."""
    state_dict = msm.state_dict()
    state_dict_json = json.dumps(state_dict)

    sql = """
        update minimizer_state
        set state_dict = ?
        where grp = ?
        """
    con.execute(sql, (state_dict_json, group))


def load_minimizer(
    con: sqlite3.Connection, group: str, minimizer_cls: ManualMinimizerType
) -> Optional[ManualMinimizer]:
    """Load the minimizer from db."""
    sql = """
        select state_dict
        from minimizer_state
        where grp = ?
        """
    cur = con.execute(sql, (group,))
    rows = cur.fetchall()
    if not rows:
        return None

    (state_dict_json,) = rows[0]
    state_dict = json.loads(state_dict_json)
    msm = minimizer_cls()
    msm.load_state_dict(state_dict)
    return msm


def load_all_minimizers(
    con: sqlite3.Connection, minimizer_cls: ManualMinimizerType
) -> dict[str, ManualMinimizer]:
    """Load all minimizers from db."""
    sql = """
        select grp, state_dict
        from minimizer_state
        """
    cur = con.execute(sql)

    minimizers = {}
    for group, state_dict_json in cur:
        state_dict = json.loads(state_dict_json)
        msm = minimizer_cls()
        msm.load_state_dict(state_dict)
        minimizers[group] = msm

    return minimizers


def make_state_df(minimizers: dict[str, ManualMinimizer]) -> pd.DataFrame:
    """Export the current results as a dataframe."""
    columns = ["group", "target", "nevals", "best_param", "best_metric", "complete"]
    data = []
    for group, msm in minimizers.items():
        best_x, best_y, is_optimal = msm.current_best()

        row = (
            group,
            msm.target_y,
            len(msm.eval_cache),
            best_x,
            best_y,
            int(is_optimal),
        )
        data.append(row)

    df = pd.DataFrame(data, columns=columns)
    return df
