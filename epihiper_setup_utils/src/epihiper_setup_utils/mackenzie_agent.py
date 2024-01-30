"""EpiHiper agent for Mackenzie."""

from pathlib import Path
from functools import partial

import click

from mackenzie.agent.main import agent_main, SetupTaskType, GetTaskResultType

from .env_file import EnvironmentConfig
from . import calibration_handler as calib
from . import projection_handler as proj


@click.command()
@click.option(
    "-e",
    "--env-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="environment config file.",
)
@click.option(
    "-o",
    "--output-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Root of the output directory to setup.",
)
def mackenzie_agent(env_file: Path, output_root: Path):
    """Run a MacKenzie agent."""
    env = EnvironmentConfig(env_file)

    type_setup_task: dict[str, SetupTaskType] = {}
    type_get_task_result: dict[str, GetTaskResultType] = {}

    type_setup_task["calibration"] = partial(calib.setup_task, env, output_root)
    type_get_task_result["calibration"] = partial(calib.get_task_result, env, output_root)

    type_setup_task["projection"] = partial(proj.setup_task, env, output_root)
    type_get_task_result["projection"] = partial(proj.get_task_result, env, output_root)

    return agent_main(type_setup_task, type_get_task_result)
