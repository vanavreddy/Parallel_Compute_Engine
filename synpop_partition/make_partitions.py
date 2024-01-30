#!/usr/bin/env python
"""Submit epihiper partition jobs."""

import os
import shlex
from pathlib import Path
from subprocess import run
from textwrap import dedent

from rich.console import Console
from rich.syntax import Syntax
from rich.pretty import pprint

MULTIPLIERS = [8, 12, 16]
PIPELINE_SBATCH_ARGS = os.environ["PIPELINE_SBATCH_ARGS"]

def print_cmd(cmd: str, console: Console):
    cmd = dedent(cmd).strip()
    syntax = Syntax(cmd, "bash")
    console.print(syntax)


def main():
    console = Console()

    synpop_list_file = "synpop_list.txt"
    synpops = Path(synpop_list_file).read_text().split()

    for synpop in synpops:
        for multiplier in MULTIPLIERS:
            cmd = f"""
                sbatch
                    --job-name partition:{synpop}:{multiplier}
                    {PIPELINE_SBATCH_ARGS}
                    --partition bii
                    --ntasks 1
                    --cpus-per-task 2
                    --mem-per-cpu 4G
                    --time 2:00:00
                    --output /scratch/%u/var/log/%x-%j.out
                    ./partition_main.sh run_epihiper_parition
                """
            print_cmd(cmd, console)
            cmd = shlex.split(cmd)

            env = {"SYNPOP": str(synpop), "MULTIPLIER": str(multiplier)}
            pprint({"env": env}, console=console)
            env = os.environ | env

            run(cmd, env=env, capture_output=False, check=True)
            exit()

if __name__ == "__main__":
    main()
