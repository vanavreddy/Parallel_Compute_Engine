"""Create EpiHiper Calibration Tasks using Bayesian Optimzier."""

import logging

import apsw
import click
import pandas as pd
from pydantic import BaseModel

from mackenzie.controller.main import ControllerProxy

from ..calibration_setup import CalibTask, CalibTaskData
from ..calibration_handler import CalibTaskResult
from ..calibration_setup_parser import (
    CalibrationCell,
    CalibrationPlace,
    ParamRanges,
    parse_calibration_setup,
    CalibrationSetup,
)
from ..minimizer.bayes_opt_minimizer import (
    BayesOptMinimizer,
    MinimizationComplete,
)
from ..minimizer import minimizer_db as mdb

from .config import get_bots_config

logger = logging.getLogger(__name__)


class BayesOptMinimizerContext(BaseModel):
    run: str
    setup: str
    cell: str
    place: str
    multiplier: int
    max_runtime: str
    task_priority: int
    param_ranges: ParamRanges


def do_create_minimizer(
    con: apsw.Connection,
    run_name: str,
    setup: CalibrationSetup,
    cell: CalibrationCell,
    place: CalibrationPlace,
    multiplier: int,
    max_runtime: str,
    init_evals: int,
    explore_evals: int,
    exploit_evals: int,
    parallel_evals: int,
    kappa_initial: float,
    kappa_scale: float,
) -> str:
    min_id = f"{run_name}:{setup.setup_name}:{cell.cell_name}:{place.place_name}"
    logger.info("Creating minimzer: %s", min_id)
    minimizer = BayesOptMinimizer(
        n_dims=len(cell.param_ranges.parameters),
        init_evals=init_evals,
        explore_evals=explore_evals,
        exploit_evals=exploit_evals,
        parallel_evals=parallel_evals,
        kappa_initial=kappa_initial,
        kappa_scale=kappa_scale,
    )
    min_context = BayesOptMinimizerContext(
        run=run_name,
        setup=setup.setup_name,
        cell=cell.cell_name,
        place=place.place_name,
        multiplier=multiplier,
        max_runtime=max_runtime,
        task_priority=place.priority,
        param_ranges=cell.param_ranges,
    )

    min_state_json = minimizer.state_dict_json()
    min_context_json = min_context.json()

    try:
        mdb.add_minimizer(
            con=con,
            min_id=min_id,
            min_type="csm",
            min_state=min_state_json,
            min_context=min_context_json,
        )
    except apsw.ConstraintError:
        pass
    return min_id


def create_minimizers(
    con: apsw.Connection,
    run_name: str,
    setup: CalibrationSetup,
    multiplier: int,
    max_runtime: str,
    init_evals: int,
    explore_evals: int,
    exploit_evals: int,
    parallel_evals: int,
    kappa_initial: float,
    kappa_scale: float,
) -> list[str]:
    min_ids = []

    for cell in setup.cells:
        for place in cell.places:
            min_id = do_create_minimizer(
                con=con,
                run_name=run_name,
                setup=setup,
                cell=cell,
                place=place,
                multiplier=multiplier,
                max_runtime=max_runtime,
                init_evals=init_evals,
                explore_evals=explore_evals,
                exploit_evals=exploit_evals,
                parallel_evals=parallel_evals,
                kappa_initial=kappa_initial,
                kappa_scale=kappa_scale,
            )
            min_ids.append(min_id)

    return min_ids


def do_create_next_task(
    controller: ControllerProxy,
    min_id: str,
    task_group: str,
    round: int,
    context: BayesOptMinimizerContext,
    raw_params: list[float],
) -> None:
    task_id = task_group
    output_dir = (
        f"{context.run}/{context.setup}/{context.cell}/{context.place}/round_{round}"
    )

    logger.info("Creating task: %s", task_id)
    task_data = CalibTask(
        task_id=task_id,
        task_data=CalibTaskData(
            setup_name=context.setup,
            cell=context.cell,
            place=context.place,
            raw_params=raw_params,
            multiplier=context.multiplier,
            max_runtime=context.max_runtime,
        ),
        output_dir=output_dir,
        minimizer_id=min_id,
        task_group=task_group,
        num_replicates=1,
    )
    task_type = "calibration"
    task_priority = context.task_priority

    controller.add_new_task(
        task_id=task_id,
        task_type=task_type,
        task_data_json=task_data.json(),
        task_priority=task_priority,
    )


def create_initial_tasks(
    min_id: str,
    minimizer: BayesOptMinimizer,
    context: BayesOptMinimizerContext,
    controller: ControllerProxy,
):
    for i, next_x in enumerate(minimizer.get_initial_xs()):
        task_group = f"{min_id}:{i}"

        do_create_next_task(
            controller=controller,
            min_id=min_id,
            task_group=task_group,
            round=i,
            context=context,
            raw_params=next_x,
        )


def create_next_task(
    min_id: str,
    minimizer: BayesOptMinimizer,
    context: BayesOptMinimizerContext,
    controller: ControllerProxy,
):
    round = minimizer.points_probed
    task_group = f"{min_id}:{round}"

    try:
        next_x = minimizer.get_next_x()
        if next_x is None:
            logger.info("Waiting for more tasks to complete: %s", min_id)
            return
    except MinimizationComplete:
        logger.info("Minimization complete for: %s", min_id)
        return

    do_create_next_task(
        controller=controller,
        min_id=min_id,
        task_group=task_group,
        round=round,
        context=context,
        raw_params=next_x,
    )


def handle_completed_tasks(con: apsw.Connection, controller: ControllerProxy):
    for (
        task_id,
        task_type,
        task_data_json,
        task_result_json,
    ) in controller.get_all_completed_tasks():
        if task_type == "calibration":
            logger.info("task completed: task_id=%s", task_id)
            controller.set_task_processed(task_id)

            task_data = CalibTask.parse_raw(task_data_json)
            task_result = CalibTaskResult.parse_raw(task_result_json)

            ret = mdb.get_minimizer(con, task_data.minimizer_id)
            assert ret is not None, f"Minimizer {task_data.minimizer_id} not found"
            min_state_json, min_context_json = ret
            minimizer = BayesOptMinimizer.from_state_dict_json(min_state_json)
            min_context = BayesOptMinimizerContext.parse_raw(min_context_json)

            minimizer.set_y(task_data.task_data.raw_params, [task_result.objective])
            create_next_task(task_data.minimizer_id, minimizer, min_context, controller)

            min_state_json = minimizer.state_dict_json()
            mdb.update_minimizer(con, task_data.minimizer_id, min_state_json)


def get_param(x: float, min: float, max: float) -> float:
    return x * (max - min) + min


def get_params(xs: list[float], param_ranges: ParamRanges) -> str:
    params = []
    for x, param in zip(xs, param_ranges.parameters):
        p = get_param(x, param.min, param.max)
        params.append(f"{param.name}={p}")
    params = ";".join(params)
    return params


@click.command()
def bayes_opt_task_source():
    logger.info("getting bayesian optimizer task source config")
    config = get_bots_config()

    logger.info("initializing minimizer db")
    con = apsw.Connection(str(config.work_dir / "minimizer.db"))
    con.execute("pragma busy_timeout=1800;")
    mdb.init_minimizer_db(con)

    controller = ControllerProxy(
        host=config.controller_host,
        port=config.controller_port,
        key_file=str(config.key_file),
        cert_file=str(config.cert_file),
    )

    setup = parse_calibration_setup(config.setup_dir)
    min_ids = create_minimizers(
        con=con,
        run_name=config.run_name,
        setup=setup,
        multiplier=config.multiplier,
        max_runtime=config.max_runtime,
        init_evals=config.init_evals,
        explore_evals=config.explore_evals,
        exploit_evals=config.exploit_evals,
        parallel_evals=config.parallel_evals,
        kappa_initial=config.kappa_initial,
        kappa_scale=config.kappa_scale,
    )

    for min_id in min_ids:
        ret = mdb.get_minimizer(con, min_id)
        assert ret is not None, f"Minimizer {min_id} not found"

        min_state_json, min_context_json = ret
        minimizer = BayesOptMinimizer.from_state_dict_json(min_state_json)
        min_context = BayesOptMinimizerContext.parse_raw(min_context_json)

        if minimizer.points_probed == 0:
            create_initial_tasks(min_id, minimizer, min_context, controller)

            min_state_json = minimizer.state_dict_json()
            mdb.update_minimizer(con, min_id, min_state_json)

    while True:
        handle_completed_tasks(con=con, controller=controller)

        statuses = []
        for (
            min_id,
            min_state_json,
            min_type,
            min_context_json,
        ) in mdb.get_all_minimizers(con):
            min_type = min_type
            minimizer = BayesOptMinimizer.from_state_dict_json(min_state_json)
            min_context = BayesOptMinimizerContext.parse_raw(min_context_json)
            status = minimizer.status()
            status["run"] = min_context.run
            status["setup"] = min_context.setup
            status["cell"] = min_context.cell
            status["place"] = min_context.place
            status["best_seen_params"] = get_params(
                status["best_seen_x"], min_context.param_ranges
            )
            status["best_pred_params"] = get_params(
                status["best_pred_x"], min_context.param_ranges
            )
            statuses.append(status)

        status_df = pd.DataFrame(statuses)
        # columns = "run,setup,cell,place,best_x,best_params,best_y,n_evals,state".split()
        # status_df = status_df[columns]
        status_df.to_csv(config.work_dir / "status.csv", index=False)
