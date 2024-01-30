"""Handler for EpiHiper Projection Tasks."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from .env_file import EnvironmentConfig
from .common_setup import mkdir_output_dir, check_epihiper_successful
from .projection_setup import ProjTask, setup_projection

logger = logging.getLogger(__name__)


class ProjTaskResult(BaseModel):
    cluster: str
    output_dir: str


def setup_task(
    env: EnvironmentConfig, output_root: Path, setup_root: Path, task_data: Any
) -> tuple[Path, int, int]:
    """Setup task."""
    task = ProjTask.parse_obj(task_data)
    logger.info("setting up task %s", task.task_id)

    output_dir = output_root / task.output_dir
    mkdir_output_dir(output_dir)

    task_data_file = output_dir / "taskData.json"
    task_data_file.write_text(json.dumps(task_data))

    sbatch_script_file, load, max_fails = setup_projection(
        env, setup_root, task_data_file, output_dir
    )
    return (sbatch_script_file, load, max_fails)


def get_task_result(
    env: EnvironmentConfig, output_root: Path, setup_root: Path, task_data: Any
) -> Optional[dict[str, Any]]:
    """Get the task result."""
    setup_root = setup_root

    task = ProjTask.parse_obj(task_data)
    output_dir = output_root / task.output_dir

    if not check_epihiper_successful(output_dir):
        return None

    return ProjTaskResult(cluster=env.env.cluster, output_dir=str(output_dir)).dict()
