"""Minimize function with Bayesian Optimization."""

import json
import random
from typing import Iterable, Optional

import numpy as np
from scipy.stats.qmc import Sobol
from bayes_opt import BayesianOptimization, UtilityFunction
from bayes_opt.util import NotUniqueError

from . import MinimizationComplete


def params_to_x(params: dict[str, float]) -> list[float]:
    return [params[f"x{i}"] for i in range(len(params))]


def x_to_params(x: list[float]) -> dict[str, float]:
    return {f"x{i}": v for i, v in enumerate(x)}

def is_similar(x: list[float], bs: list[list[float]]) -> bool:
    nx = np.array(x)
    for b in bs:
        nb = np.array(b)
        if np.linalg.norm(nx-nb, ord=2) < 1e-6:
            return True
    return False

def nudge_x(x: list[float]) -> list[float]:
    nx = np.array(x)
    noise = np.random.normal(0, 1e-2, size=len(x))
    nx = nx + noise
    nx = np.clip(nx, a_min=0.0, a_max=1.0)
    x = nx.tolist()
    return x

def ensure_not_similar(x: list[float], bs: list[list[float]]) -> list[float]:
    while is_similar(x, bs):
        x = nudge_x(x)
    return x



class BayesOptMinimizer:
    """Minimize a stochastic function using Bayesian Optimization."""

    def __init__(
        self,
        n_dims: int,
        init_evals: int = 32,
        explore_evals: int = 32,
        exploit_evals: int = 32,
        parallel_evals: int = 10,
        kappa_initial: float = 2.576,
        kappa_scale: float = 0.95,
    ):
        """Initialize.

        Since we use Sobol sequences for intialization,
        init_evals needs to be a power of 2
        """
        self.n_dims = n_dims
        self.init_evals = init_evals
        self.explore_evals = explore_evals
        self.exploit_evals = exploit_evals
        self.parallel_evals = parallel_evals
        self.kappa_initial = kappa_initial
        self.kappa_scale = kappa_scale
        self.state = "running"

        self.eval_cache: list[tuple[list[float], float]] = []
        self.points_probed: int = 0

        bounds = [(0.0, 1.0) for _ in range(self.n_dims)]
        self.optimizer = BayesianOptimization(
            f=None,
            pbounds={f"x{i}": b for i, b in enumerate(bounds)},
            verbose=2,
            random_state=1,
        )
        self.utility = UtilityFunction(kind="ucb", kappa=self.kappa_initial, xi=0.0)

    def state_dict_json(self) -> str:
        return json.dumps(
            dict(
                n_dims=self.n_dims,
                init_evals=self.init_evals,
                explore_evals=self.explore_evals,
                exploit_evals=self.exploit_evals,
                parallel_evals=self.parallel_evals,
                kappa_initial=self.kappa_initial,
                kappa_scale=self.kappa_scale,
                state=self.state,
                eval_cache=list(self.eval_cache),
                points_probed=self.points_probed,
                utility_kappa=self.utility.kappa,
            )
        )

    @classmethod
    def from_state_dict_json(cls, state_dict_json: str):
        state_dict = json.loads(state_dict_json)
        obj = cls(
            n_dims=state_dict["n_dims"],
            init_evals=state_dict["init_evals"],
            explore_evals=state_dict["explore_evals"],
            exploit_evals=state_dict["exploit_evals"],
            parallel_evals=state_dict["parallel_evals"],
            kappa_initial=state_dict["kappa_initial"],
            kappa_scale=state_dict["kappa_scale"],
        )

        obj.state = state_dict["state"]
        obj.eval_cache = list(state_dict["eval_cache"])
        obj.points_probed = state_dict["points_probed"]

        for x, y in obj.eval_cache:
            params = x_to_params(x)
            # Note here we send -y to optimizer as target.
            # Bayesian optimizer tries to maximize.
            # We are trying to minimize.
            # But we keep the true value in the eval cache
            try:
                obj.optimizer.register(params=params, target=-y)
            except (KeyError, NotUniqueError):
                pass
        obj.utility.kappa = state_dict["utility_kappa"]

        return obj

    def get_initial_xs(self) -> list[list[float]]:
        qmc_gen = Sobol(d=self.n_dims, scramble=True)
        init_points = qmc_gen.random(self.init_evals)
        ret = [init_points[i].tolist() for i in range(self.init_evals)]

        par_points = np.random.uniform(0.0, 1.0, (self.parallel_evals, self.n_dims))
        ret.extend([par_points[i].tolist() for i in range(self.parallel_evals)])

        self.points_probed += len(ret)
        return ret

    def get_next_x(self) -> Optional[list[float]]:
        if len(self.eval_cache) < self.init_evals:
            return None

        explore_end = self.init_evals + self.parallel_evals + self.explore_evals
        if self.points_probed < explore_end:
            # Exploration phase
            ret = self.optimizer.suggest(self.utility)
            ret = params_to_x(ret)
            ret = ensure_not_similar(ret, [x for x, _ in self.eval_cache])
            self.points_probed += 1
            return ret

        all_evals = self.init_evals + self.parallel_evals + self.explore_evals + self.exploit_evals
        if self.points_probed < all_evals:
            # Exploitation phase
            ret = self.optimizer.suggest(self.utility)
            ret = params_to_x(ret)
            ret = ensure_not_similar(ret, [x for x, _ in self.eval_cache])
            self.utility.kappa *= self.kappa_scale
            self.points_probed += 1
            return ret

        self.state = "all points probed"
        raise MinimizationComplete()

    def set_y(self, x: list[float], ys: list[float]) -> None:
        assert len(x) == self.n_dims

        params = x_to_params(x)
        for y in ys:
            # Note here we send -y to optimizer as target.
            # Bayesian optimizer tries to maximize.
            # We are trying to minimize.
            # But we keep the true value in the eval cache
            try:
                self.optimizer.register(params=params, target=-y)
            except (KeyError, NotUniqueError):
                pass
            self.eval_cache.append((x, y))

    def status(self) -> dict:
        NAN = float("nan")

        if self.eval_cache:
            max = self.optimizer.max
            assert max["params"] is not None
            assert max["target"] is not None
            best_seen_x = params_to_x(max["params"])
            best_seen_y = -max["target"]

            utility = UtilityFunction(kind="ucb", kappa=0.0, xi=0.0)
            best_pred_x = self.optimizer.suggest(utility)
            arr = self.optimizer._space.params_to_array(best_pred_x)
            best_pred_y_mean, best_pred_y_std = self.optimizer._gp.predict(arr.reshape(1, -1), return_std=True)

            best_pred_x = params_to_x(best_pred_x)
            best_pred_y_mean = -float(best_pred_y_mean.squeeze())
            best_pred_y_std = float(best_pred_y_std.squeeze())
        else:
            best_seen_x = [NAN] * self.n_dims
            best_seen_y = NAN
            best_pred_x = [NAN] * self.n_dims
            best_pred_y_mean, best_pred_y_std = NAN, NAN

        return dict(
            best_seen_x=best_seen_x,
            best_seen_y=best_seen_y,
            best_pred_x=best_pred_x,
            best_pred_y_mean=best_pred_y_mean,
            best_pred_y_std=best_pred_y_std,
            points_probed=self.points_probed,
            points_seen=len(self.eval_cache),
            state=self.state,
        )
