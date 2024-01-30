"""Common stuff for calibration pipelines."""

import json
import math
import gzip
import logging
from typing import Optional, cast
from pathlib import Path

# from functools import cache

from dotenv import dotenv_values

log = logging.getLogger(__name__)


def get_environment(env_file: Path | str) -> dict[str, str]:
    env_file = str(env_file)
    env = dotenv_values(env_file)
    env = cast(dict[str, str], env)
    return env


def get_partition_args(synpop: str, multipiler: int, env_file: Path | str) -> str:
    env = get_environment(env_file)
    partition_cache_dir = env["PARTITION_CACHE_DIR"]
    partition_args_file = f"{partition_cache_dir}/{synpop}/{multipiler}/sbatch_args.txt"
    partition_args = Path(partition_args_file).read_text()
    return partition_args


def get_load(synpop: str, multipiler: int, env_file: Path | str) -> int:
    env = get_environment(env_file)
    partition_cache_dir = env["PARTITION_CACHE_DIR"]
    partition_config_file = f"{partition_cache_dir}/{synpop}/{multipiler}/config.json"
    partition_config = Path(partition_config_file).read_text()
    partition_config = json.loads(partition_config)
    load = partition_config["numberOfParts"]
    return load


def check_epihiper_successful(output_dir: Path) -> bool:
    """Check if the EpiHiper simulation finshed successfully."""
    try:
        output_dir = Path(output_dir)
        run_params_file = output_dir / "config.json"

        run_parameters = json.loads(run_params_file.read_text(encoding="utf-8"))

        # Check the status file
        status_file = Path(run_parameters["status"])
        status = json.loads(status_file.read_text(encoding="utf-8"))
        assert status["status"] == "completed", "Status not completed"
        assert status["progress"] == 100, "Status progress not 100"

        # Ensure output file has non zero size
        output_file = Path(run_parameters["output"] + ".gz")
        assert output_file.stat().st_size > 0, "Output file empty"

        # Ensure the summary output file has non zero size
        summary_output_file = Path(run_parameters["summaryOutput"] + ".gz")
        assert summary_output_file.stat().st_size > 0, "Summary output empty"

        # Ensure the last tick of summary output is same as the number of ticks
        end_tick = run_parameters["endTick"]
        with gzip.open(summary_output_file, "rt") as fobj:
            last_line = ""
            for line in fobj:
                last_line = line
        last_line = last_line.strip().split(",")
        assert end_tick == int(
            last_line[0]
        ), "Summary last line doesn't correspond to end tick"

        return True
    except Exception as e:
        log.debug("EpiHiper succesful completion can't be verfied: %s", e)
        return False


def get_estimated_R(output_dir: Path | str) -> Optional[float]:
    """Get the estimated R from the output directory."""
    try:
        output_dir = Path(output_dir)
        estimated_R_file = output_dir / "estimated_R.txt"
        estimated_R = float(estimated_R_file.read_text())
        if math.isfinite(estimated_R):
            return estimated_R
        else:
            log.debug(
                "Estimated R read from %s is not finite (= %s)", output_dir, estimated_R
            )
            return None
    except Exception as e:
        log.debug("Failed to read estimated_R from %s: %s", output_dir, e)
        return None


def get_fitting_error(output_dir: Path | str) -> Optional[float]:
    """Get the fitting error from the output directory."""
    try:
        output_dir = Path(output_dir)
        fitting_error_file = output_dir / "fitting_error.txt"
        fitting_error = float(fitting_error_file.read_text())
        return fitting_error
        # if math.isfinite(fitting_error):
        #     return fitting_error
        # else:
        #     log.debug(
        #         "Fitting error read from %s is not finite (= %s)",
        #         output_dir,
        #         fitting_error,
        #     )
        #     return None
    except Exception as e:
        log.debug("Failed to read fitting error from %s: %s", output_dir, e)
        return None
