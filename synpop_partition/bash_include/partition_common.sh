# Run EpiHiper Partition

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

do_run_epihiper_parition_ex_usa () {
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
        --contact-network-file "$SYNPOP_ROOT/$SYNPOP"/*_epihiper_export_network.txt \
        --persontrait-file "$SYNPOP_ROOT/$SYNPOP"/*_persontrait_epihiper.txt \
        --output-directory "$OUTPUT_DIR" \
        --cluster "$CLUSTER" \
        --multiplier "$MULTIPLIER"

    # Run EpiHiper Partition
    do_run_epihiper_parition

    echo "Partitioning completed successfully"
    exit 0
}

