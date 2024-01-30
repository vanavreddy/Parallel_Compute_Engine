"""Common functions for the calibration pipeline using estimated R."""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, cast
from dataclasses import dataclass
from collections import defaultdict

import click
import pandas as pd

from slurm_pipeline import (
    add_task,
    count_live_tasks,
    init_task_db,
    set_task_processed,
    process_running,
    process_failed,
    process_ready,
)

from scalar_minimizer import (
    ManualScalarMinimizer,
    MinimzationSuccess,
    MinimzationFailed,
    add_minimizer,
    init_minimizer_db,
    load_all_minimizers,
    load_minimizer,
    update_minimizer,
    make_state_df,
)

from pipeline_common import (
    get_estimated_R,
    get_partition_args,
    get_load,
    check_epihiper_successful,
)

SQLITE3_TIMEOUT = 300


@dataclass
class CalibrationSetup:
    # Path under which we have the state configs
    config_root: Path

    # Path to the base disease model file
    base_disease_model_file: Path

    # Path to the calibration file
    calibration_file: Path


@dataclass
class CalibrationConfig:
    # Memory multipler for estimating memory usage of sims
    multiplier: int

    # Number of replicates to run per round
    num_replicates: int

    # Relative tolerace to decide if sim is calibrated
    r_tol: float

    # Tau range to calibrate over
    tau_range: tuple[float, float]

    # Environment file
    env_file: Path

    # File containing list of available synthetic populations
    synpop_list_file: Path

    # Setups to calibrate
    setups: dict[str, CalibrationSetup]

    # Path to output dir root
    output_root: Path

    # Sbatch args to use for sim jobs for the current run
    pipeline_sbatch_args: str

    # When submitting jobs don't exceed more than this compute load
    max_load: int

    # Path to the pipeline task database file
    pipeline_db_file: Path

    # Path to the calibration status file
    status_file: Path

    # Max fails per sim
    max_fails: int

    # EpiHiper command
    epihiper_command: str


log = logging.getLogger(__name__)

_GLOBAL_CONFIG: Optional[CalibrationConfig] = None


def get_config() -> CalibrationConfig:
    assert _GLOBAL_CONFIG is not None
    return _GLOBAL_CONFIG


def set_config(cfg: CalibrationConfig) -> None:
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = cfg


def add_calib_task(
    con: sqlite3.Connection,
    setup: str,
    state: str,
    synpop: str,
    round_: int,
    replicate: int,
    transmissibility: float,
) -> None:
    """Add a calibration task to slurm pipeline task queue."""
    cfg = get_config()

    task_id = f"calib:{setup}:{state}:{round_}:{replicate}"
    output_dir = (
        f"{cfg.output_root}/{setup}/{state}/round_{round_}/replicate_{replicate}"
    )

    task_meta = {
        "setup": setup,
        "state": state,
        "synpop": synpop,
        "round": round_,
        "replicate": replicate,
        "transmissibility": transmissibility,
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

    cell_config_dir = cfg.setups[setup].config_root
    cell_config_dir = f"{cell_config_dir}/{state}"

    base_disease_model_file = cfg.setups[setup].base_disease_model_file

    sbatch_env = {
        "SYNPOP": synpop,
        "MULTIPLIER": cfg.multiplier,
        "CELL_CONFIG_DIR": cell_config_dir,
        "BASE_DISEASE_MODEL_FILE": base_disease_model_file,
        "TRANSMISSIBILITY": transmissibility,
        "REPLICATE": replicate,
        "OUTPUT_DIR": output_dir,
    }

    load = get_load(synpop, cfg.multiplier, cfg.env_file)
    priority = 1
    max_fails = cfg.max_fails

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
    """Check if a calibration job was successful."""
    _ = task_id

    output_dir = Path(task_meta["output_dir"])
    if not check_epihiper_successful(output_dir):
        return False
    R = get_estimated_R(output_dir)
    if R is None:
        return False

    return True


def process_all_completed(
    con: sqlite3.Connection,
    setup: str,
    state: str,
    synpop: str,
    completed_tasks: list[tuple[str, dict]],
):
    """Process the tasks for which all replicates have completed."""
    cfg = get_config()

    # Mark all the completed tasks as processed
    for task_id, _ in completed_tasks:
        set_task_processed(con, task_id)
        log.info(
            "Task processed: task_id = %s",
            task_id,
        )

    # Collect all the outp
    xs: list[float] = []
    ys: list[float] = []
    for _, task_meta in completed_tasks:
        output_dir = task_meta["output_dir"]
        x = task_meta["transmissibility"]
        y = get_estimated_R(output_dir)
        assert y is not None, f"Failed to get estimated_R from {output_dir}"

        xs.append(x)
        ys.append(y)

    all_xs_equal = all(x == xs[0] for x in xs)
    assert all_xs_equal, f"All transmissibilites not same for same round {xs}"

    group = f"{setup}:{state}"
    msm = load_minimizer(con, group, ManualScalarMinimizer)
    assert msm is not None, f"Minimizer for {group} not found"
    try:
        mean_y = sum(ys) / len(ys)
        msm.set_y(xs[0], mean_y)

        try:
            next_x = msm.next_x()
        except MinimzationSuccess as e:
            log.info(
                "Calibration success: setup=%s, state=%s, transmissibility=%s, R=%s",
                setup,
                state,
                e.x,
                e.y,
            )
            return
        except MinimzationFailed as e:
            log.warning(
                "Calibration failed: setup=%s, state=%s, transmissibility=%s, R=%s",
                setup,
                state,
                e.x,
                e.y,
            )
            return

        round_ = len(msm.eval_cache)
    finally:
        update_minimizer(con, group, msm)

    for replicate in range(cfg.num_replicates):
        add_calib_task(
            con=con,
            setup=setup,
            state=state,
            synpop=synpop,
            round_=round_,
            replicate=replicate,
            transmissibility=next_x,
        )


def process_completed(con: sqlite3.Connection):
    """Process the completed tasks."""
    cfg = get_config()

    sql = """
        select task_id, task_meta
        from task
        where state = 'completed'
        """
    cur = con.execute(sql)

    group_completed_tasks = defaultdict(list)
    for (
        task_id,
        task_meta_json,
    ) in cur:
        task_meta = json.loads(task_meta_json)
        setup = task_meta["setup"]
        state = task_meta["state"]
        synpop = task_meta["synpop"]
        group_completed_tasks[setup, state, synpop].append((task_id, task_meta))
    group_completed_tasks.default_factory = None

    for (setup, state, synpop), completed_tasks in group_completed_tasks.items():
        if len(completed_tasks) != cfg.num_replicates:
            continue

        process_all_completed(con, setup, state, synpop, completed_tasks)


@click.group()
def cli():
    """R Estimation Calibration Pipeline."""


@cli.command()
def init():
    """Initalize the pipeline."""
    cfg = get_config()

    log.info("Trying to create output root.")
    cfg.output_root.mkdir(mode=0o770, parents=True, exist_ok=False)

    log.info("Initializing task database.")
    con = sqlite3.connect(cfg.pipeline_db_file, timeout=SQLITE3_TIMEOUT)

    init_task_db(con)
    init_minimizer_db(con)

    log.info("Loading state list.")
    synpops = cfg.synpop_list_file.read_text().split()

    # Check to see if synpop name and state name will be same or not
    # It is not same for detailed us population
    # It is same for crude world populations
    if synpops[0].startswith("usa_") and synpops[0].endswith("_2017_SynPop"):
        states = [s.removeprefix("usa_").removesuffix("_2017_SynPop") for s in synpops]
    else:
        states = synpops

    with con:
        for setup in cfg.setups:
            log.info("Loading calibration file for %s", setup)
            calibration_file = cfg.setups[setup].calibration_file
            calib_df = pd.read_csv(calibration_file)
            state_target_r = dict(zip(calib_df.state, calib_df.target_r))  # type: ignore

            for state, synpop in zip(states, synpops):
                group = f"{setup}:{state}"

                msm = ManualScalarMinimizer(
                    min_x=cfg.tau_range[0],
                    max_x=cfg.tau_range[1],
                    target_y=state_target_r[state],
                    tol=cfg.r_tol,
                )
                first_x = msm.next_x()

                log.info("Initalizing minimizers for %s", group)
                add_minimizer(con, group, msm)

                log.info("Creating tasks for %s", group)
                for replicate in range(cfg.num_replicates):
                    add_calib_task(
                        con=con,
                        setup=setup,
                        state=state,
                        synpop=synpop,
                        round_=0,
                        replicate=replicate,
                        transmissibility=first_x,
                    )

        minimizers = load_all_minimizers(con, ManualScalarMinimizer)
        state_df = make_state_df(minimizers)
        state_df.to_csv(cfg.status_file, index=False, na_rep="NA")


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
            process_completed(con)
            process_ready(con, max_load=cfg.max_load)

            minimizers = load_all_minimizers(con, ManualScalarMinimizer)
            state_df = make_state_df(minimizers)
            state_df.to_csv(cfg.status_file, index=False, na_rep="NA")

            live_tasks = count_live_tasks(con)
            if live_tasks == 0:
                log.info("No more live tasks; exiting")
                return


@cli.command()
def update_tau_range():
    """Update tau range."""
    cfg = get_config()

    log.info("Connecting to task database.")
    con = sqlite3.connect(cfg.pipeline_db_file, timeout=SQLITE3_TIMEOUT)

    with con:
        minimizers = load_all_minimizers(con, ManualScalarMinimizer)
        minimizers = cast(dict[str, ManualScalarMinimizer], minimizers)
        for group, msm in minimizers.items():
            msm.min_x = cfg.tau_range[0]
            msm.max_x = cfg.tau_range[1]
            msm.update_min_max()
            update_minimizer(con, group, msm)


def estimate_R_calib_main(config: CalibrationConfig) -> None:
    """Main entry point for the calibration setup."""

    set_config(config)
    logging.basicConfig(level=logging.DEBUG)
    cli()
