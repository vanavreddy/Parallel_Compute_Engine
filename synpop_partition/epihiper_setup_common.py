"""EpiHiper setup script helpers."""

import shutil
from typing import cast
from pathlib import Path

import click
from dotenv import dotenv_values


def ensure_absolute(p: str | Path) -> Path:
    """Ensure the returned path is absolute."""
    p = Path(p)
    p = p if p.is_absolute() else Path.cwd() / p
    return p


def copy_file_and_return_new_path(src: Path, dst_dir: Path) -> Path:
    """Copy file."""
    dst = dst_dir / src.name
    shutil.copyfile(src, dst)
    return dst


def parse_start_end_tick(cell_env_file: Path) -> tuple[int, int]:
    """Parse start and end tick from cell_env."""
    cell_env = dotenv_values(cell_env_file)
    cell_env = cast(dict[str, str], cell_env)
    start_tick = int(cell_env["START_TICK"])
    end_tick = int(cell_env["END_TICK"])

    return start_tick, end_tick


class CellConfigDirType(click.ParamType):
    name = "directory"

    def convert(self, value, param, ctx):
        cell_config_dir = Path(value)
        if not cell_config_dir.is_dir():
            self.fail(f"{value!r} is not an existing directory", param, ctx)

        traits_file = cell_config_dir / "traits"
        if not traits_file.exists():
            self.fail("Traits file doesn't exist", param, ctx)

        disease_model_file = cell_config_dir / "diseaseModel"
        if not disease_model_file.exists():
            self.fail("Disease model file not found.", param, ctx)

        initialization_file = cell_config_dir / "initialization"
        if not initialization_file.exists():
            self.fail("Initialization file not found.", param, ctx)

        intervention_file = cell_config_dir / "intervention"
        if not intervention_file.exists():
            self.fail("Intervention file not found.", param, ctx)

        # cell_env_file = cell_config_dir / "cell_env.sh"
        # if not cell_env_file.exists():
        #     self.fail("Cell env file not found.", param, ctx)

        input_run_params_file = cell_config_dir / "runParameters.json"
        if not input_run_params_file.exists():
            self.fail("Run Parameters file not found.", param, ctx)

        return str(cell_config_dir)


opt_ContactNetworkFile = click.option(
    "-cn",
    "--contact-network-file",
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    required=True,
    help="Path to partitioned contact network file.",
)

opt_PersontraitFile = click.option(
    "-pt",
    "--persontrait-file",
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    required=True,
    help="Path to persontrait file.",
)

opt_CellConfigDir = click.option(
    "-cc",
    "--cell-config-directory",
    "cell_config_dir",
    type=CellConfigDirType(),
    required=True,
    help="Path to the cell configuration directory.",
)

opt_DbHost = click.option(
    "-dh",
    "--db-host",
    type=str,
    required=True,
    help="Synthetic population database hostname (host[:port]).",
)

opt_Replicate = click.option(
    "-r",
    "--replicate",
    type=int,
    default=0,
    show_default=True,
    help="The current replicate.",
)

opt_LogLevel = click.option(
    "-ll",
    "--log-level",
    type=str,
    default="warn",
    show_default=True,
    help="EpiHiper log level.",
)

opt_OutputDir = click.option(
    "-o",
    "--output-directory",
    "output_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Path to output directory.",
)
