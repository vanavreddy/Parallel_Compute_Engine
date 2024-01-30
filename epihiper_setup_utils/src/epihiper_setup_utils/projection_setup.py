"""Projection setup."""

import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined
from pydantic import BaseModel


from .env_file import EnvironmentConfig
from .common_setup import setup_run_parameters


class ProjTaskData(BaseModel):
    setup_name: str
    cell: str
    place: str
    batch: int
    replicate: int
    multiplier: int
    max_runtime: str


class ProjTask(BaseModel):
    task_id: str
    task_data: ProjTaskData
    output_dir: str  # Relateive Path


def setup_projection(
    env: EnvironmentConfig, setup_root: Path, task_data_file: Path, output_dir: Path
) -> tuple[Path, int, int]:
    """Setup for calibration."""
    task = ProjTask.parse_file(task_data_file)
    task_data = task.task_data

    cluster = env.env.cluster

    loader = PackageLoader("epihiper_setup_utils")
    tenv = Environment(loader=loader, undefined=StrictUndefined)

    fname = f"epihiper_proj_{cluster}.sbatch.jinja2"
    template = tenv.get_template(fname)

    # Copy the contents of the file
    src_dir = setup_root / task_data.setup_name / task_data.cell / task_data.place
    shutil.copytree(src=src_dir, dst=output_dir, dirs_exist_ok=True)

    # Setup the output directory
    setup_run_parameters(output_dir, env, task_data.place, task_data.multiplier)

    # Compute load and max fails
    load = env.get_load(task_data.place, task_data.multiplier)
    max_fails = env.env.max_fails

    # Create the sbatch script
    sbatch_script_contents = template.render(
        job_name=task.task_id,
        sbatch_job_args=env.get_job_sbatch_args(task_data.place, task_data.multiplier),
        max_runtime=task_data.max_runtime,
        sbatch_pipeline_args=env.env.pipeline_sbatch_args,
        env_file_contents=env.env_file_contents,
        common_dir=str(setup_root / task_data.setup_name / task_data.cell),
        output_dir=str(output_dir),
    )
    sbatch_script_file = output_dir / "run_script.sbatch"
    sbatch_script_file.write_text(sbatch_script_contents)
    return (sbatch_script_file, load, max_fails)
