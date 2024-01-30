"""EpiHiper Setup Utils."""

import sys
import logging
from pathlib import Path

import click

from .env_file import EnvironmentConfig
from .calibration_setup import setup_calibration
from .projection_setup import setup_projection
from .mackenzie_agent import mackenzie_agent
from .csm_task_source.main import csm_task_source
from .bayes_opt_task_source.main import bayes_opt_task_source
from .proj_task_source.main import proj_task_source
from .post_opt_task_source.main import post_opt_task_source


@click.group()
def cli():
    """EpiHiper Setup Utils."""
    logging.basicConfig(
        format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
        stream=sys.stderr,
        level=logging.INFO,
    )


@cli.command()
@click.option(
    "-e",
    "--env-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="Environment config file.",
)
@click.option(
    "-s",
    "--setup-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing the setup configs.",
)
@click.option(
    "-t",
    "--task-data-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="Task data file.",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Output directory to setup.",
)
def calibration(
    env_file: Path, setup_root: Path, task_data_file: Path, output_dir: Path
):
    """Setup for calibration."""
    env = EnvironmentConfig(env_file)

    sbatch_script_file, load, _ = setup_calibration(
        env, setup_root, task_data_file, output_dir
    )
    print("Setup complete")
    print("sbatch file: %s" % sbatch_script_file)
    print("compute load: %d" % load)


@cli.command()
@click.option(
    "-e",
    "--env-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="Environment config file.",
)
@click.option(
    "-s",
    "--setup-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing the setup configs.",
)
@click.option(
    "-t",
    "--task-data-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="Task data file.",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Output directory to setup.",
)
def projection(
    env_file: Path, setup_root: Path, task_data_file: Path, output_dir: Path
):
    """Setup for projection."""
    env = EnvironmentConfig(env_file)

    sbatch_script_file, load, _ = setup_projection(
        env, setup_root, task_data_file, output_dir
    )
    print("Setup complete")
    print("sbatch file: %s" % sbatch_script_file)
    print("compute load: %d" % load)


cli.add_command(mackenzie_agent)
cli.add_command(csm_task_source)
cli.add_command(bayes_opt_task_source)
cli.add_command(post_opt_task_source)
cli.add_command(proj_task_source)


if __name__ == "__main__":
    cli(prog_name="epihiper-setup-utils")
