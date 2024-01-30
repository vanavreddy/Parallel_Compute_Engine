"""Minimize a scalar."""

import sys
import math

from scipy.optimize import OptimizeResult, minimize_scalar
from more_itertools import tail
from pydantic import BaseModel

from . import MinimizationComplete

EPSILON = 1e-9


class _UnknownEvaluation(Exception):
    def __init__(self, x: float):
        super().__init__()
        self.x = x


class CachedValue(BaseModel):
    x: float
    y: float
    raw_ys: list[float]


class MinimizerState(BaseModel):
    max_evals: int
    n_iter_no_change: int
    min_rel_improvement: float
    make_y_positive: bool
    state: str
    eval_cache: list[CachedValue]


class ConvexScalarMinimizer:
    """Minimize a convex scalar function."""

    def __init__(
        self,
        max_evals: int = 100,
        n_iter_no_change: int = 3,
        min_rel_improvement: float = 0.01,
        make_y_positive: bool = True,
    ):
        self.state = MinimizerState(
            max_evals=max_evals,
            n_iter_no_change=n_iter_no_change,
            min_rel_improvement=min_rel_improvement,
            make_y_positive=make_y_positive,
            state="running",
            eval_cache=[],
        )

    def state_dict_json(self) -> str:
        return self.state.json()

    @classmethod
    def from_state_dict_json(cls, state_dict_json: str):
        obj = cls()
        obj.state = MinimizerState.parse_raw(state_dict_json)
        return obj

    @staticmethod
    def _round(x: float) -> float:
        return round(x, 6)

    def _fun(self, x: float) -> float:
        x = self._round(x)
        ecache = {cv.x: cv.y for cv in self.state.eval_cache}
        if x in ecache:
            return ecache[x]

        raise _UnknownEvaluation(x)

    def do_run_minimizer(self) -> OptimizeResult:
        # Run the minimizer
        kwargs = {
            "bounds": (0.0, 1.0),
            "options": {"maxiter": int(1e6)},
            "method": "bounded",
        }
        return minimize_scalar(self._fun, **kwargs)

    def stop_early(self) -> bool:
        no_improvement = 0
        best_y = sys.float_info.max
        for cv in tail(self.state.n_iter_no_change + 1, self.state.eval_cache):
            improvement = (best_y - cv.y) / abs(best_y)
            if improvement < self.state.min_rel_improvement:
                no_improvement += 1
            else:
                no_improvement = 0

            if cv.y < best_y:
                best_y = cv.y
                if best_y == 0.0:
                    best_y = EPSILON

        if no_improvement >= self.state.n_iter_no_change:
            return True
        else:
            return False

    def get_next_x(self) -> float:
        if self.stop_early():
            self.state.state = "early stopping condition reached"
            raise MinimizationComplete()
        if len(self.state.eval_cache) >= self.state.max_evals:
            self.state.state = "max evaluations reached"
            raise MinimizationComplete()

        try:
            result = self.do_run_minimizer()
            if result.success:
                self.state.state = f"optimizer succeeded: {result.message}"
                raise MinimizationComplete()
            else:
                self.state.state = f"optimizer failed: {result.message}"
                raise MinimizationComplete()
        except _UnknownEvaluation as e:
            return e.x

    def set_ys(self, x: float, raw_ys: list[float]) -> None:
        x = self._round(x)

        finite_ys = [y for y in raw_ys if math.isfinite(y)]
        if finite_ys:
            y = sum(finite_ys) / len(finite_ys)
        else:
            if self.state.eval_cache:
                y = max(cv.y for cv in self.state.eval_cache)
            else:
                y = sys.float_info.max

        if self.state.make_y_positive:
            y = abs(y)

        self.state.eval_cache.append(CachedValue(x=x, y=y, raw_ys=raw_ys))

    def status(self) -> dict:
        if self.state.eval_cache:
            cvs = sorted(enumerate(self.state.eval_cache), key=lambda x: x[1].y)
            best_round = cvs[0][0]
            best_x = cvs[0][1].x
            best_y = cvs[0][1].y
        else:
            best_round = float("nan")
            best_x = float("nan")
            best_y = float("nan")

        n_evals = len(self.state.eval_cache)
        return dict(
            best_round=best_round,
            best_x=best_x,
            best_y=best_y,
            n_evals=n_evals,
            state=self.state.state,
        )
