"""Calibration setup."""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined
from pydantic import BaseModel


from .env_file import EnvironmentConfig
from .common_setup import setup_run_parameters
from .calibration_setup_parser import ParamRanges


class CalibTaskData(BaseModel):
    setup_name: str
    cell: str
    place: str
    raw_params: list[float]
    multiplier: int
    max_runtime: str


class CalibTask(BaseModel):
    task_id: str
    task_data: CalibTaskData
    output_dir: str  # Relateive Path

    minimizer_id: str
    task_group: str
    num_replicates: int


def setup_update_params(range_file: Path, raw_params: list[float], output_dir: Path):
    """Create update.json file."""
    print("range_file:", range_file)
    param_ranges = ParamRanges.parse_file(range_file)
    print("param_ranges:", param_ranges)

    if len(param_ranges.parameters) != len(raw_params):
        n_opt_params = len(param_ranges.parameters)
        n_raw_params = len(raw_params)
        msg = f"""
            Number of parameters mismatch.
            Parameter range file has {n_opt_params} parameters,
            but the was provided {n_raw_params} values.
            """
        msg = " ".join(msg.split())
        raise ValueError(msg)

    oparams = []
    for param, xi in zip(param_ranges.parameters, raw_params):
        value = xi * (param.max - param.min) + param.min
        oparams.append(dict(name=param.name, value=value))
    oparams = {"parameters": oparams}
    print(oparams)

    opt_params_file = output_dir / "update.json"
    opt_params_file.write_text(json.dumps(oparams))


def setup_calibration(
    env: EnvironmentConfig, setup_root: Path, task_data_file: Path, output_dir: Path
) -> tuple[Path, int, int]:
    """Setup for calibration."""
    task = CalibTask.parse_file(task_data_file)
    task_data = task.task_data

    cluster = env.env.cluster

    loader = PackageLoader("epihiper_setup_utils")
    tenv = Environment(loader=loader, undefined=StrictUndefined)

    fname = f"epihiper_calib_{cluster}.sbatch.jinja2"
    template = tenv.get_template(fname)

    # Copy the contents of the file
    src_dir = setup_root / task_data.setup_name / task_data.cell / task_data.place
    shutil.copytree(src=src_dir, dst=output_dir, dirs_exist_ok=True)

    # Setup the output directory
    setup_run_parameters(output_dir, env, task_data.place, task_data.multiplier)

    # Create update.json for parameter update
    range_file = setup_root / task_data.setup_name / task_data.cell / "range.json"
    setup_update_params(range_file, task_data.raw_params, output_dir)

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
