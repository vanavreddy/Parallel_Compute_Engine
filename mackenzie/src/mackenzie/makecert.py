"""Create a pair to certificate files."""

import shlex
from subprocess import run

import click


@click.command()
@click.argument("name")
def makecert(name):
    """Create a pair to certificate files."""
    cmd = f"""
        openssl req -newkey rsa:4096
        -x509
        -sha256
        -days 3650
        -nodes
        -out '{name}.crt'
        -keyout '{name}.key'
        -subj '/CN=common'
    """
    cmd = shlex.split(cmd)
    run(cmd)


if __name__ == "__main__":
    makecert()
