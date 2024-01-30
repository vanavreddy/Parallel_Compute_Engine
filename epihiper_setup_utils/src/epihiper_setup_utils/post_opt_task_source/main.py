"""Create EpiHiper Tasks using Optimizer Results."""

import logging

import json
import click
import pandas as pd
from pydantic import BaseModel

from mackenzie.controller.main import ControllerProxy

from ..calibration_setup import CalibTask, CalibTaskData
from ..calibration_setup_parser import (
    ParamRanges,
    parse_calibration_setup,
)

from .config import get_pots_config

logger = logging.getLogger(__name__)


class PostOptimizerContext(BaseModel):
    run: str
    setup: str
    cell: str
    place: str
    multiplier: int
    max_runtime: str
    task_priority: int
    param_ranges: ParamRanges


def do_create_next_task(
    controller: ControllerProxy,
    min_id: str,
    task_group: str,
    replicate: int,
    context: PostOptimizerContext,
    raw_params: list[float],
) -> None:
    task_id = f"{task_group}:{replicate}"
    output_dir = f"{context.run}/{context.setup}/{context.cell}/{context.place}/post_opt_runs/replicate_{replicate}"

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

    try:
        controller.add_new_task(
            task_id=task_id,
            task_type=task_type,
            task_data_json=task_data.json(),
            task_priority=task_priority,
        )
    except Exception as e:
        logging.warning("failed to add task: %s : %s", task_id, e)


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
def post_opt_task_source():
    logger.info("getting bayesian optimizer task source config")
    config = get_pots_config()

    controller = ControllerProxy(
        host=config.controller_host,
        port=config.controller_port,
        key_file=str(config.key_file),
        cert_file=str(config.cert_file),
    )

    opt_status_df = pd.read_csv(config.opt_status_file)
    opt_x = dict()
    for cell, place, pred_x in zip(
        opt_status_df.cell, opt_status_df.place, opt_status_df.best_pred_x
    ):
        opt_x[cell, place] = json.loads(pred_x)

    setup = parse_calibration_setup(config.setup_dir)

    for cell in setup.cells:
        for place in cell.places:
            logger.info(
                "cell=%s, place=%s, best_x=%s",
                cell.cell_name,
                place.place_name,
                opt_x[cell.cell_name, place.place_name],
            )

    for cell in setup.cells:
        for place in cell.places:
            min_id = f"{config.run_name}:{setup.setup_name}:{cell.cell_name}:{place.place_name}"

            for replicate in range(config.num_evals):
                do_create_next_task(
                    controller=controller,
                    min_id=min_id,
                    task_group=f"post_opt:{min_id}",
                    replicate=replicate,
                    context=PostOptimizerContext(
                        run=config.run_name,
                        setup=setup.setup_name,
                        cell=cell.cell_name,
                        place=place.place_name,
                        multiplier=config.multiplier,
                        max_runtime=config.max_runtime,
                        task_priority=place.priority,
                        param_ranges=cell.param_ranges,
                    ),
                    raw_params=opt_x[cell.cell_name, place.place_name],
                )
