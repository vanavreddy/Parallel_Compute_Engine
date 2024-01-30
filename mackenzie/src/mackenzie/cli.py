"""Mackenize multi cluster scheduler."""

import sys
import logging

import click

from .makecert import makecert
from .controller.main import controller
from .cmd.main import add_setup


@click.group()
def cli():
    """Mackenize multi cluster scheduler."""
    logging.basicConfig(
        format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
        stream=sys.stderr,
        level=logging.INFO,
    )


cli.add_command(makecert)
cli.add_command(controller)
cli.add_command(add_setup)

if __name__ == "__main__":
    cli(prog_name="mackenzie")
