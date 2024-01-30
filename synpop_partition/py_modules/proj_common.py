"""Common functions for the state projection pipeline."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import click

from slurm_pipeline import (
    add_task,
    count_live_tasks,
    init_task_db,
    process_running,
    process_failed,
    process_ready,
)

from pipeline_common import get_partition_args, get_load, check_epihiper_successful

log = logging.getLogger(__name__)

SQLITE3_TIMEOUT = 300


@dataclass
class ProjectionConfig:
    # Memory multipler for estimating memory usage of sims
    multiplier: int

    # Start batch number
    start_batch: int

    # Number of replicates per batch
    batch_num_replicates: list[int]

    # Environment file
    env_file: Path

    # File containing list of available synthetic populations
    synpop_list_file: Path

    # Cell base dir ; the directory containing the cell configs
    cell_base_dir: Path

    # Name of the cells
    cells: list[str]

    # Path to output dir root
    output_root: Path

    # Sbatch args to use for sim jobs for the current run
    pipeline_sbatch_args: str

    # When submitting jobs don't exceed more than this compute load
    max_load: int

    # Path to the pipeline task database file
    pipeline_db_file: Path

    # Max fails per sim
    max_fails: int

    # EpiHiper command
    epihiper_command: str


_GLOBAL_CONFIG: Optional[ProjectionConfig] = None


def get_config() -> ProjectionConfig:
    assert _GLOBAL_CONFIG is not None
    return _GLOBAL_CONFIG


def set_config(cfg: ProjectionConfig) -> None:
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = cfg


def add_proj_task(
    con: sqlite3.Connection,
    cell: str,
    state: str,
    synpop: str,
    batch: int,
    replicate: int,
) -> None:
    cfg = get_config()

    task_id = f"proj:{cell}:{state}:{batch}:{replicate}"
    output_dir = f"{cfg.output_root}/batch_{batch}/{cell}/{state}/replicate_{replicate}"

    task_meta = {
        "cell": cell,
        "state": state,
        "synpop": synpop,
        "replicate": replicate,
        "output_dir": output_dir,
    }

    partition_args = get_partition_args(synpop, cfg.multiplier, cfg.env_file)
    sbatch_cmd = f"""
    sbatch
        --job-name {task_id}
        {cfg.pipeline_sbatch_args}
        {partition_args}
        --output "{output_dir}/slurm-%j.out"
        {cfg.epihiper_command}
    """

    cell_config_dir = cfg.cell_base_dir / cell / state

    sbatch_env = {
        "SYNPOP": synpop,
        "MULTIPLIER": cfg.multiplier,
        "CELL_CONFIG_DIR": cell_config_dir,
        "REPLICATE": replicate,
        "OUTPUT_DIR": output_dir,
    }

    load = get_load(synpop, cfg.multiplier, cfg.env_file)
    priority = 100 - batch
    max_fails = 5

    add_task(
        con=con,
        task_id=task_id,
        task_meta=task_meta,
        sbatch_cmd=sbatch_cmd,
        sbatch_env=sbatch_env,
        output_dir=output_dir,
        load=load,
        priority=priority,
        max_fails=max_fails,
    )


def check_job_successful(task_id: str, task_meta: dict) -> bool:
    """Check if a projection job was successful."""
    _ = task_id

    output_dir = Path(task_meta["output_dir"])
    if not check_epihiper_successful(output_dir):
        return False

    return True


@click.group()
def cli():
    """Projection Pipeline."""


@cli.command()
def init():
    """Initalize the pipeline."""
    cfg = get_config()

    log.info("Trying to create output root.")
    cfg.output_root.mkdir(mode=0o770, parents=True, exist_ok=False)

    log.info("Initializing task database.")
    con = sqlite3.connect(cfg.pipeline_db_file, timeout=SQLITE3_TIMEOUT)

    init_task_db(con)

    log.info("Loading state list.")
    synpops = cfg.synpop_list_file.read_text().split()

    # Check to see if synpop name and state name will be same or not
    # It is not same for detailed us population
    # It is same for crude world populations
    if synpops[0].startswith("usa_") and synpops[0].endswith("_2017_SynPop"):
        states = [s.removeprefix("usa_").removesuffix("_2017_SynPop") for s in synpops]
    else:
        states = synpops

    log.info("Creating tasks.")
    with con:
        for cell in cfg.cells:
            for state, synpop in zip(states, synpops):
                for batch, num_replicates in enumerate(
                    cfg.batch_num_replicates, start=cfg.start_batch
                ):
                    for replicate in range(num_replicates):
                        add_proj_task(
                            con=con,
                            cell=cell,
                            state=state,
                            synpop=synpop,
                            batch=batch,
                            replicate=replicate,
                        )


@cli.command()
def run():
    """Run the pipeline."""
    cfg = get_config()

    log.info("Connecting to task database.")
    con = sqlite3.connect(cfg.pipeline_db_file, timeout=SQLITE3_TIMEOUT)

    while True:
        with con:
            process_running(con, check_job_successful)
            process_failed(con)
            process_ready(con, max_load=cfg.max_load)

            live_tasks = count_live_tasks(con)
            if live_tasks == 0:
                log.info("No more live tasks; exiting")
                return


def proj_main(config: ProjectionConfig) -> None:
    """Main entry point for the projection pipeline."""

    set_config(config)
    logging.basicConfig(level=logging.DEBUG)
    cli()
