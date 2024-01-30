"""EpiHiper partition setup."""

import math
import json
from pathlib import Path

import click

from epihiper_setup_common import ensure_absolute


def awsslurm_get_num_parts_sbatch_args(job_mem_gb: int) -> tuple[int, str]:
    """Return the number of partitions on rivanna."""
    MEM_PER_NODE = 360  # GB
    TASKS_PER_NODE = 40
    CPUS_PER_TASK = 1

    MEM_PER_TASK = MEM_PER_NODE / TASKS_PER_NODE

    if job_mem_gb <= MEM_PER_NODE:
        num_parts = math.ceil(job_mem_gb / MEM_PER_TASK)
    else:
        num_parts = math.ceil(job_mem_gb / MEM_PER_NODE) * TASKS_PER_NODE

    if num_parts < TASKS_PER_NODE:
        args = f"""
            --nodes 1
            --ntasks-per-node {num_parts}
            --cpus-per-task {CPUS_PER_TASK}
            --mem-per-cpu 9G
            --partition bii
            """
    else:
        assert num_parts % TASKS_PER_NODE == 0

        args = f"""
            --nodes {num_parts // TASKS_PER_NODE}
            --ntasks-per-node {TASKS_PER_NODE}
            --cpus-per-task {CPUS_PER_TASK}
            --mem-per-cpu 9G
            --partition bii
            """
    args = " ".join(args.split())

    return num_parts, args


def rivanna_get_num_parts_sbatch_args(job_mem_gb: int) -> tuple[int, str]:
    """Return the number of partitions on rivanna."""
    MEM_PER_NODE = 360  # GB
    TASKS_PER_NODE = 40
    CPUS_PER_TASK = 1

    MEM_PER_TASK = MEM_PER_NODE / TASKS_PER_NODE

    if job_mem_gb <= MEM_PER_NODE:
        num_parts = math.ceil(job_mem_gb / MEM_PER_TASK)
    else:
        num_parts = math.ceil(job_mem_gb / MEM_PER_NODE) * TASKS_PER_NODE

    if num_parts < TASKS_PER_NODE:
        args = f"""
            --nodes 1
            --ntasks-per-node {num_parts}
            --cpus-per-task {CPUS_PER_TASK}
            --mem-per-cpu 9G
            --partition bii
            """
    else:
        assert num_parts % TASKS_PER_NODE == 0

        args = f"""
            --nodes {num_parts // TASKS_PER_NODE}
            --ntasks-per-node {TASKS_PER_NODE}
            --cpus-per-task {CPUS_PER_TASK}
            --mem-per-cpu 9G
            --partition bii
            """
    args = " ".join(args.split())

    return num_parts, args


def bridges2_get_num_parts_sbatch_args(job_mem_gb: int) -> tuple[int, str]:
    """Return the number of partitions on bridges2."""
    MEM_PER_NODE = 256  # GB
    TASKS_PER_NODE = 64
    CPUS_PER_TASK = 2

    MEM_PER_TASK = MEM_PER_NODE / TASKS_PER_NODE

    if job_mem_gb < 0.5 * MEM_PER_NODE:
        num_parts = math.ceil(job_mem_gb / MEM_PER_TASK)
    else:
        num_parts = math.ceil(job_mem_gb / MEM_PER_NODE) * TASKS_PER_NODE

    if num_parts <= 32:
        args = f"""
            --nodes 1
            --ntasks-per-node {num_parts}
            --cpus-per-task {CPUS_PER_TASK}
            --mem-per-cpu 2000M
            --partition RM-shared
            """
    else:
        assert num_parts % TASKS_PER_NODE == 0

        args = f"""
            --nodes {num_parts // TASKS_PER_NODE}
            --ntasks-per-node {TASKS_PER_NODE}
            --cpus-per-task {CPUS_PER_TASK}
            --partition RM
            """
    args = " ".join(args.split())

    return num_parts, args


def anvil_get_num_parts_sbatch_args(job_mem_gb: int) -> tuple[int, str]:
    """Return the number of partitions on anvil."""
    MEM_PER_NODE = 256  # GB
    TASKS_PER_NODE = 64
    CPUS_PER_TASK = 2

    MEM_PER_TASK = MEM_PER_NODE / TASKS_PER_NODE

    if job_mem_gb < 0.5 * MEM_PER_NODE:
        num_parts = math.ceil(job_mem_gb / MEM_PER_TASK)
    else:
        num_parts = math.ceil(job_mem_gb / MEM_PER_NODE) * TASKS_PER_NODE

    if num_parts <= 32:
        args = f"""
            --nodes 1
            --ntasks-per-node {num_parts}
            --cpus-per-task {CPUS_PER_TASK}
            --mem-per-cpu 2G
            --partition shared
            """
    else:
        assert num_parts % TASKS_PER_NODE == 0

        args = f"""
            --nodes {num_parts // TASKS_PER_NODE}
            --ntasks-per-node {TASKS_PER_NODE}
            --cpus-per-task {CPUS_PER_TASK}
            --partition wholenode
            """
    args = " ".join(args.split())

    return num_parts, args


def estimate_sim_mem_req(
    contact_network_path: Path, persontrait_path: Path, multiplier: float
) -> int:
    """Return the estimated memory required for simulation."""
    contact_network_path = contact_network_path.resolve()
    persontrait_path = persontrait_path.resolve()

    contact_network_size = contact_network_path.stat().st_size / (2**30)
    person_trait_size = persontrait_path.stat().st_size / (2**30)

    job_mem_gb = contact_network_size + person_trait_size
    job_mem_gb = job_mem_gb * multiplier
    job_mem_gb = math.ceil(job_mem_gb)
    job_mem_gb = int(job_mem_gb)

    return job_mem_gb


def setup_output_dir(network_file: Path, nparts: int, output_dir: Path) -> None:
    """Setup the output directory for EpiHiper partition."""
    network_file = ensure_absolute(network_file)
    output_dir = ensure_absolute(output_dir)

    output_network_file = output_dir / "contact_network.txt"
    output_network_file.symlink_to(network_file)

    conf = {
        "$schema": "../../schema/partitionSchema.json",
        "epiHiperSchema": "https://github.com/NSSAC/EpiHiper-Schema/blob/master/schema/partitionSchema.json",
        "contactNetwork": output_network_file,
        "outputDirectory": output_dir,
        "numberOfParts": nparts,
    }

    config_file = output_dir / "config.json"
    config_file.write_text(json.dumps(conf, default=str), encoding="utf-8")


@click.command()
@click.option(
    "-cn",
    "--contact-network-file",
    "contact_network_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    required=True,
    help="Path to contact network file.",
)
@click.option(
    "-pt",
    "--persontrait-file",
    "persontrait_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    required=True,
    help="Path to persontrait file.",
)
@click.option(
    "-o",
    "--output-directory",
    "output_dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    required=True,
    help="Path to output directory.",
)
@click.option(
    "-c",
    "--cluster",
    type=click.Choice(["rivanna", "bridges2", "anvil"]),
    required=True,
    help="Cluster on which partitions will be used.",
)
@click.option(
    "--multiplier",
    type=int,
    required=True,
    help="Data size to memory required multiplier.",
)
def main(contact_network_path, persontrait_path, output_dir, cluster, multiplier):
    """Setup the output directory for EpiHiper partition."""
    contact_network_path = ensure_absolute(contact_network_path)
    persontrait_path = ensure_absolute(persontrait_path)
    output_dir = ensure_absolute(output_dir)

    job_mem_gb = estimate_sim_mem_req(
        contact_network_path, persontrait_path, multiplier
    )

    match cluster:
        case "rivanna":
            num_parts, sbatch_args = rivanna_get_num_parts_sbatch_args(job_mem_gb)
        case "bridges2":
            num_parts, sbatch_args = bridges2_get_num_parts_sbatch_args(job_mem_gb)
        case "anvil":
            num_parts, sbatch_args = anvil_get_num_parts_sbatch_args(job_mem_gb)
        case "awsslurm":
            num_parts, sbatch_args = awsslurm_get_num_parts_sbatch_args(job_mem_gb)
        case _:
            raise ValueError(f"Unknown cluster {cluster}")

    setup_output_dir(contact_network_path, num_parts, output_dir)

    sbatch_args_file = output_dir / "sbatch_args.txt"
    sbatch_args_file.write_text(sbatch_args, encoding="utf-8")


if __name__ == "__main__":
    main()
