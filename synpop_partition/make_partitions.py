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

from dotenv import load_dotenv
from pathlib import Path

# read in the environment variables
dotenv_path = Path('../environment.sh')
load_dotenv(dotenv_path=dotenv_path)
PIPELINE_SBATCH_ARGS = os.environ["PIPELINE_SBATCH_ARGS"]
PARTITION = os.environ["PARTITION"]
LOG_DIR = os.environ["LOG_DIR"]

MULTIPLIERS = [8, 12, 16]

def print_cmd(cmd: str, console: Console):
    cmd = dedent(cmd).strip()
    syntax = Syntax(cmd, "bash")
    console.print(syntax)


def main():
    console = Console()

    synpop_list_file = "synpop_list.txt"
    synpops = Path(synpop_list_file).read_text().split()

    # check if the path to store logs exists
    output_path = LOG_DIR
    if not os.path.exists(output_path):
        print("Creating log dir:", output_path)
        try:
            os.mkdir(LOG_DIR)
        except:
            print("Path" , output_path, "does not exist. Create the directory and rerun this script")
            exit()

    for synpop in synpops:
        for multiplier in MULTIPLIERS:
            cmd = f"""
                sbatch
                    --job-name partition:{synpop}:{multiplier}
                    {PIPELINE_SBATCH_ARGS}
                    --partition {PARTITION}
                    --ntasks 1
                    --cpus-per-task 2
                    --time 2:00:00
                    --output {LOG_DIR}/%x-%j.out
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
