"""Create EpiHiper projection tasks."""

import logging

import click

from mackenzie.controller.main import ControllerProxy

from ..projection_setup import ProjTask, ProjTaskData
from ..projection_setup_parser import (
    parse_projection_setup,
)

from .config import get_pts_config

logger = logging.getLogger(__name__)


def do_create_next_task(
    controller: ControllerProxy,
    run: str,
    setup: str,
    cell: str,
    place: str,
    batch: int,
    replicate: int,
    priority: int,
    multiplier: int,
    max_runtime: str,
) -> None:
    task_id = f"proj:{run}:{setup}:{batch}:{cell}:{place}:{replicate}"
    output_dir = f"{run}/{setup}/batch_{batch}/{cell}/{place}/replicate_{replicate}"

    logger.info("Creating task: %s", task_id)
    task_data = ProjTask(
        task_id=task_id,
        task_data=ProjTaskData(
            setup_name=setup,
            cell=cell,
            place=place,
            multiplier=multiplier,
            max_runtime=max_runtime,
            batch=batch,
            replicate=replicate,
        ),
        output_dir=output_dir,
    )
    task_type = "projection"
    task_priority = priority

    try:
        controller.add_new_task(
            task_id=task_id,
            task_type=task_type,
            task_data_json=task_data.json(),
            task_priority=task_priority,
        )
    except Exception as e:
        logging.warning("failed to add task: %s : %s", task_id, e)


@click.command()
def proj_task_source():
    logger.info("getting projection task source config")
    config = get_pts_config()

    controller = ControllerProxy(
        host=config.controller_host,
        port=config.controller_port,
        key_file=str(config.key_file),
        cert_file=str(config.cert_file),
    )

    setup = parse_projection_setup(config.setup_dir)

    for cell in setup.cells:
        for place in cell.places:
            for batch, n_replicates in enumerate(
                config.num_replicates, config.start_batch
            ):
                priority = int(place.priority + -batch * 1e6)
                for replicate in range(n_replicates):
                    do_create_next_task(
                        controller=controller,
                        run=config.run_name,
                        setup=setup.setup_name,
                        cell=cell.cell_name,
                        place=place.place_name,
                        batch=batch,
                        replicate=replicate,
                        priority=priority,
                        multiplier=config.multiplier,
                        max_runtime=config.max_runtime,
                    )
