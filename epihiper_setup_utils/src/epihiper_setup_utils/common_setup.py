"""Common setup functions."""

import gzip
import json
import logging
from pathlib import Path

from .env_file import EnvironmentConfig


MAX_FAILS = 100

logger = logging.getLogger(__name__)


def mkdir_output_dir(output_dir: Path) -> None:
    """Create a fresh output directory.

    If the directory already exists rename it with -fail_{i} suffix,
    and create a fresh output directory.
    """
    if output_dir.exists():
        for i in range(1, MAX_FAILS + 1):
            fail_dir = str(output_dir) + f"-fail_{i}"
            fail_dir = Path(fail_dir)
            if fail_dir.exists():
                continue

            output_dir.replace(fail_dir)
            break

    output_dir.mkdir(mode=0o770, parents=True, exist_ok=False)


def setup_run_parameters(
    output_dir: Path,
    env: EnvironmentConfig,
    place: str,
    multipiler: int,
):
    """Setup runParameters.json"""
    contact_network_file = env.get_contact_network_file(place, multipiler)
    persontrait_file = env.get_persontrait_file(place)
    db_host = env.get_dbhost()
    log_level = env.env.epihiper_log_level

    traits_file = output_dir / "traits"
    disease_model_file = output_dir / "diseaseModel"
    initialization_file = output_dir / "initialization"
    intervention_file = output_dir / "intervention"
    run_params_file = output_dir / "runParameters.json"

    scenario = {
        "epiHiperSchema": "https://github.com/NSSAC/EpiHiper-Schema/blob/master/schema/modelScenarioSchema.json",
        "contactNetwork": contact_network_file,
        "personTraitDB": [persontrait_file],
        "traits": traits_file,
        "diseaseModel": disease_model_file,
        "initialization": initialization_file,
        "intervention": intervention_file,
    }
    scenario_file = output_dir / "scenario.json"
    scenario_file.write_text(json.dumps(scenario, default=str))

    run_parameters = json.loads(run_params_file.read_text())
    run_parameters.update(
        {
            "epiHiperSchema": "https://github.com/NSSAC/EpiHiper-Schema/blob/master/schema/runParametersSchema.json",
            "modelScenario": scenario_file,
            "output": output_dir / "output.csv",
            "dbHost": db_host,
            "logLevel": log_level,
            "summaryOutput": output_dir / "outputSummary.csv",
            "status": output_dir / "status.json",
            "dbMaxRecords": 1000000,
            "dbConnectionTimeout": 20,
            "dbConnectionRetries": 10,
            "dbConnectionMaxDelay": 10000,
        }
    )
    run_params_file.write_text(
        json.dumps(run_parameters, default=str), encoding="utf-8"
    )


def check_epihiper_successful(output_dir: Path) -> bool:
    """Check if the EpiHiper simulation finshed successfully."""
    try:
        output_dir = Path(output_dir)
        run_params_file = output_dir / "runParameters.json"

        run_parameters = json.loads(run_params_file.read_text(encoding="utf-8"))

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
        logger.debug("EpiHiper succesful completion can't be verfied: %s", e)
        return False
