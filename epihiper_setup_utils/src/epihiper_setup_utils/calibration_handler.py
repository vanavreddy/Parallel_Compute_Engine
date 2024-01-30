"""Handler for EpiHiper Calibration Tasks."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from .env_file import EnvironmentConfig
from .common_setup import mkdir_output_dir, check_epihiper_successful
from .calibration_setup import CalibTask, setup_calibration

logger = logging.getLogger(__name__)


class CalibTaskResult(BaseModel):
    cluster: str
    output_dir: str
    objective: float


def get_objective_output(output_dir: Path | str) -> Optional[float]:
    """Get the fitting error from the output directory."""
    try:
        output_dir = Path(output_dir)
        objective_output_file = output_dir / "objectiveOutput.txt"
        objective = float(objective_output_file.read_text())
        return objective
    except Exception as e:
        logger.debug("Failed to read objective ouptut from %s: %s", output_dir, e)
        return None


def setup_task(
    env: EnvironmentConfig, output_root: Path, setup_root: Path, task_data: Any
) -> tuple[Path, int, int]:
    """Setup task."""
    task = CalibTask.parse_obj(task_data)
    logger.info("setting up task %s", task.task_id)

    output_dir = output_root / task.output_dir
    mkdir_output_dir(output_dir)

    task_data_file = output_dir / "taskData.json"
    task_data_file.write_text(json.dumps(task_data))

    sbatch_script_file, load, max_fails = setup_calibration(
        env, setup_root, task_data_file, output_dir
    )
    return (sbatch_script_file, load, max_fails)


def get_task_result(
    env: EnvironmentConfig, output_root: Path, setup_root: Path, task_data: Any
) -> Optional[dict[str, Any]]:
    """Get the task result."""
    setup_root = setup_root

    task = CalibTask.parse_obj(task_data)
    output_dir = output_root / task.output_dir

    if not check_epihiper_successful(output_dir):
        return None

    objective = get_objective_output(output_dir)
    if objective is None:
        return None

    return CalibTaskResult(
        cluster=env.env.cluster, output_dir=str(output_dir), objective=objective
    ).dict()
