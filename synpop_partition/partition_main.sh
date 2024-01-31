#!/bin/bash
# State pipeline entry point

# Path to the current script.
# Note when this script is submitted to slurm,
# Slurm will make a copy and put it in some some other place.
# So do not use this variable when running via slurm.
CUR_SCRIPT="$(realpath "${BASH_SOURCE[0]}")"

# This will change form time to time
# Things to include: account, reservation, qos, etc.
# Things not to include here: partition, time, output, jobname, etc.

# Source the environment
. "../environment.sh"
export PYTHONPATH

cmd_run_epihiper_parition () {
    . "../environment.sh"
    . "module_setup.sh"
    . "$CODE_DIR/bash_include/partition_common.sh"

    do_run_epihiper_parition_usa
}

cmd_default () {

read -r -d '' SUBCOMMANDS <<'EOF'
run_epihiper_parition
EOF

    set -Eeuo pipefail

    CMD=$(echo "$SUBCOMMANDS" | "$FZF_CMD")
    "$CUR_SCRIPT" "$CMD"
    exit 0
}

# Execute the function called

if [[ -z "$1" ]] ; then
    SUBCOMMAND="default"
else
    SUBCOMMAND="$1"
    shift 1
fi

if [[ "$( type -t "cmd_${SUBCOMMAND}" )" != "function" ]] ; then
    err "Invalid command: $SUBCOMMAND"
    usage
    exit 1
fi

"cmd_${SUBCOMMAND}" "$@"
exit 0
