"""Command line inteface for interacting with MacKenzie controller."""

import shlex
from pathlib import Path
from subprocess import run

import click

from .config import get_cmd_config
from ..controller.main import ControllerProxy


@click.command()
@click.option(
    "-d",
    "--setup-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="A directory containing epihiper setup.",
)
def add_setup(setup_dir):
    """Add a setup to the controller."""
    click.secho("Getting cmd config")
    config = get_cmd_config()

    setup_dir = Path(setup_dir)
    setup_name = setup_dir.name

    setup_tar_file = Path.cwd() / f"{setup_name}.tar.gz"
    cmd = f"tar -C '{setup_dir.parent}' -czf '{setup_tar_file}' '{setup_name}'"
    click.secho("creating setup tar file: %s" % cmd, fg="yellow")
    cmd = shlex.split(cmd)
    run(cmd, check=True)

    setup_dir_tar = setup_tar_file.read_bytes()

    click.secho("Connecting to controller")
    controller = ControllerProxy(
        host=config.controller_host,
        port=config.controller_port,
        key_file=str(config.key_file),
        cert_file=str(config.cert_file),
    )

    controller.add_setup(setup_name, setup_dir_tar)
    click.secho(f"Setup '{setup_name}' added successfully", fg="green")
