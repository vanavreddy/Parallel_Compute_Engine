#!/bin/bash
# State pipeline entry point

# Path to the current script.
# Note when this script is submitted to slurm,
# Slurm will make a copy and put it in some some other place.
# So do not use this variable when running via slurm.
CUR_SCRIPT="$(realpath "${BASH_SOURCE[0]}")"

# Source the environment
. "../environment.sh"
export PYTHONPATH

do_run_epihiper_parition_usa () {
    set -Eeuo pipefail

    # Inputs to be passed in via env variables
    echo "SYNPOP=$SYNPOP"
    echo "MULTIPLIER=$MULTIPLIER"

    set -x

    # Create output directory
    OUTPUT_DIR="$PARTITION_CACHE_DIR/$SYNPOP/$MULTIPLIER"
    if [[ -e "$OUTPUT_DIR" ]] ; then
        rm -rf "$OUTPUT_DIR"
    fi
    mkdir -p "$OUTPUT_DIR"

    # Setup output directory
    "$PYTHON_EXE" "$CODE_DIR/epihiper_partition_setup.py" \
        --contact-network-file "$SYNPOP_ROOT/$SYNPOP"/*_contact_network_config_*-contact_0_with_lid.txt \
        --persontrait-file "$SYNPOP_ROOT/$SYNPOP"/*_persontrait_epihiper.txt \
        --output-directory "$OUTPUT_DIR" \
        --cluster "$CLUSTER" \
        --multiplier "$MULTIPLIER"

    # Run EpiHiper Partition
    do_run_epihiper_parition

    echo "Partitioning completed successfully"
    exit 0
}

cmd_run_epihiper_parition () {
    . "../environment.sh"
    . "module_setup.sh"

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
