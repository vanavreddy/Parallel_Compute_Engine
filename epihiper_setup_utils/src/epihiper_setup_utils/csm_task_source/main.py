"""Create EpiHiper Calibration Tasks using Convex Scalar Minimizer."""

import logging
from collections import defaultdict

import apsw
import click
import pandas as pd
from pydantic import BaseModel

from mackenzie.controller.main import ControllerProxy

from ..calibration_setup import CalibTask, CalibTaskData
from ..calibration_handler import CalibTaskResult
from ..calibration_setup_parser import (
    ParamRange,
    CalibrationCell,
    CalibrationPlace,
    parse_calibration_setup,
    CalibrationSetup,
)
from ..minimizer.convex_scalar_minimizer import (
    ConvexScalarMinimizer,
    MinimizationComplete,
)
from ..minimizer import minimizer_db as mdb

from .config import get_csmts_config

logger = logging.getLogger(__name__)


class CsmMinimizerContext(BaseModel):
    run: str
    setup: str
    cell: str
    place: str
    num_replicates: int
    multiplier: int
    max_runtime: str
    task_priority: int
    param_range: ParamRange


def do_create_minimizer(
    con: apsw.Connection,
    run_name: str,
    setup: CalibrationSetup,
    cell: CalibrationCell,
    place: CalibrationPlace,
    num_replicates: int,
    multiplier: int,
    max_runtime: str,
    max_evals: int,
    n_iter_no_change: int,
    min_rel_improvement: float,
    make_y_positive: bool,
) -> str:
    min_id = f"{run_name}:{setup.setup_name}:{cell.cell_name}:{place.place_name}"
    logger.info("Creating minimzer: %s", min_id)
    minimizer = ConvexScalarMinimizer(
        max_evals=max_evals,
        n_iter_no_change=n_iter_no_change,
        min_rel_improvement=min_rel_improvement,
        make_y_positive=make_y_positive,
    )
    min_context = CsmMinimizerContext(
        run=run_name,
        setup=setup.setup_name,
        cell=cell.cell_name,
        place=place.place_name,
        num_replicates=num_replicates,
        multiplier=multiplier,
        max_runtime=max_runtime,
        task_priority=place.priority,
        param_range=cell.param_ranges.parameters[0],
    )

    min_state_json = minimizer.state_dict_json()
    min_context_json = min_context.json()
    mdb.add_minimizer(
        con=con,
        min_id=min_id,
        min_type="csm",
        min_state=min_state_json,
        min_context=min_context_json,
    )
    return min_id


def create_minimizers(
    con: apsw.Connection,
    run_name: str,
    setup: CalibrationSetup,
    num_replicates: int,
    multiplier: int,
    max_runtime: str,
    max_evals: int,
    n_iter_no_change: int,
    min_rel_improvement: float,
    make_y_positive: bool,
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
                num_replicates=num_replicates,
                multiplier=multiplier,
                max_runtime=max_runtime,
                max_evals=max_evals,
                n_iter_no_change=n_iter_no_change,
                min_rel_improvement=min_rel_improvement,
                make_y_positive=make_y_positive,
            )
            min_ids.append(min_id)

    return min_ids


def do_create_next_task(
    controller: ControllerProxy,
    min_id: str,
    task_group: str,
    round: int,
    replicate: int,
    context: CsmMinimizerContext,
    raw_params: list[float],
) -> None:
    task_id = f"{task_group}:{replicate}"
    output_dir = (
        f"{context.run}/{context.setup}/{context.cell}/{context.place}"
        f"/round_{round}/replicate_{replicate}"
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
        num_replicates=context.num_replicates,
    )
    task_type = "calibration"
    task_priority = context.task_priority

    controller.add_new_task(
        task_id=task_id,
        task_type=task_type,
        task_data_json=task_data.json(),
        task_priority=task_priority,
    )


def create_next_tasks(
    min_id: str,
    minimizer: ConvexScalarMinimizer,
    context: CsmMinimizerContext,
    controller: ControllerProxy,
):
    round = len(minimizer.state.eval_cache)
    task_group = f"{min_id}:{round}"
    try:
        next_x = minimizer.get_next_x()
    except MinimizationComplete:
        logger.info("Minimization complete for: %s", min_id)
        return

    for replicate in range(context.num_replicates):
        do_create_next_task(
            controller=controller,
            min_id=min_id,
            task_group=task_group,
            round=round,
            replicate=replicate,
            context=context,
            raw_params=[next_x],
        )


class GroupedDatum(BaseModel):
    task_ids: list[str] = []
    num_replicates: int = 0
    min_id: str = ""
    x: float = 0.0
    ys: list[float] = []


def do_group_completed_tasks(
    completed_tasks: list[tuple[str, str, str, str]]
) -> dict[str, GroupedDatum]:
    grouped_data = defaultdict(GroupedDatum)
    for (
        task_id,
        task_type,
        task_data_json,
        task_result_json,
    ) in completed_tasks:
        if task_type == "calibration":
            task_data = CalibTask.parse_raw(task_data_json)
            task_result = CalibTaskResult.parse_raw(task_result_json)

            task_group = task_data.task_group
            gd = grouped_data[task_group]
            gd.task_ids.append(task_id)
            gd.num_replicates = task_data.num_replicates
            gd.min_id = task_data.minimizer_id
            gd.x = task_data.task_data.raw_params[0]
            gd.ys.append(task_result.objective)

    return grouped_data


def do_handle_completed_group(
    con: apsw.Connection, controller: ControllerProxy, gd: GroupedDatum
) -> None:
    for task_id in gd.task_ids:
        controller.set_task_processed(task_id)

    ret = mdb.get_minimizer(con, gd.min_id)
    assert ret is not None, f"Minimizer {gd.min_id} not found"
    min_state_json, min_context_json = ret
    minimizer = ConvexScalarMinimizer.from_state_dict_json(min_state_json)
    min_context = CsmMinimizerContext.parse_raw(min_context_json)

    minimizer.set_ys(gd.x, gd.ys)
    create_next_tasks(gd.min_id, minimizer, min_context, controller)

    min_state_json = minimizer.state_dict_json()
    mdb.update_minimizer(con, gd.min_id, min_state_json)


def handle_completed_tasks(con: apsw.Connection, controller: ControllerProxy):
    grouped_data = do_group_completed_tasks(controller.get_all_completed_tasks())

    # Process the groups
    for task_group, gd in grouped_data.items():
        if gd.num_replicates != len(gd.ys):
            continue

        logger.info("task group completed: task_group=%s", task_group)
        do_handle_completed_group(con, controller, gd)


@click.command()
def csm_task_source():
    logger.info("getting convex scalar minimizer task source config")
    config = get_csmts_config()

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
        num_replicates=config.num_replicates,
        multiplier=config.multiplier,
        max_runtime=config.max_runtime,
        max_evals=config.max_evals,
        n_iter_no_change=config.n_iter_no_change,
        min_rel_improvement=config.min_rel_improvement,
        make_y_positive=config.make_y_positive,
    )

    for min_id in min_ids:
        ret = mdb.get_minimizer(con, min_id)
        assert ret is not None, f"Minimizer {min_id} not found"
        min_state_json, min_context_json = ret
        minimizer = ConvexScalarMinimizer.from_state_dict_json(min_state_json)
        min_context = CsmMinimizerContext.parse_raw(min_context_json)

        create_next_tasks(min_id, minimizer, min_context, controller)

    while True:
        handle_completed_tasks(con=con, controller=controller)

        statuses = []
        for (
            min_id,
            min_state_json,
            min_type,
            min_context_json,
        ) in mdb.get_all_minimizers(con):
            if min_type != "csm":
                continue

            minimizer = ConvexScalarMinimizer.from_state_dict_json(min_state_json)
            min_context = CsmMinimizerContext.parse_raw(min_context_json)
            status = minimizer.status()
            status["run"] = min_context.run
            status["setup"] = min_context.setup
            status["cell"] = min_context.cell
            status["place"] = min_context.place
            status["best_param"] = (
                status["best_x"]
                * (min_context.param_range.max - min_context.param_range.min)
                + min_context.param_range.min
            )
            statuses.append(status)

        status_df = pd.DataFrame(statuses)
        #columns = "run,setup,cell,place,best_x,best_param,best_y,n_evals,state".split()
        #status_df = status_df[columns]
        status_df.to_csv(config.work_dir / "status.csv", index=False)
