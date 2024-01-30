# Run EpiHiper in Projection Mode

do_run_epihiper_proj () {
    set -Eeuo pipefail

    # Inputs to be passed in via env variables
    echo "SYNPOP=$SYNPOP"
    echo "MULTIPLIER=$MULTIPLIER"
    echo "CELL_CONFIG_DIR=$CELL_CONFIG_DIR"
    echo "REPLICATE=$REPLICATE"
    echo "OUTPUT_DIR=$OUTPUT_DIR"

    set -x

    # Check output directory exists
    if [[ ! -d "$OUTPUT_DIR" ]] ; then
        echo "$OUTPUT_DIR doesn't exist"
        exit 1
    fi

    # Get the db host
    DB_HOST="$(cat "$DBHOST_IP_FILE" )"

    # Setup output directory
    "$PYTHON_EXE" "$CODE_DIR/epihiper_setup.py" \
        --contact-network-file "$PARTITION_CACHE_DIR/$SYNPOP/$MULTIPLIER"/contact_network.txt \
        --persontrait-file "$SYNPOP_ROOT/$SYNPOP"/*_persontrait_epihiper.txt \
        --cell-config-directory "$CELL_CONFIG_DIR" \
        --db-host "$DB_HOST" \
        --replicate "$REPLICATE" \
        --log-level "$EPIHIPER_LOG_LEVEL" \
        --output-directory "$OUTPUT_DIR"

    # Check for addNoise.sh
    if [[ -e "$OUTPUT_DIR/addNoise.sh" ]] ; then
        set +x
        OLDPATH="$PATH"
        export PATH="$NODE_CONDA_ENV/bin:$PATH"
        set -x

        pushd "$OUTPUT_DIR"
        chmod +x addNoise.sh
        ./addNoise.sh
        popd

        set +x
        export PATH="$OLDPATH"
        set -x
    fi

    # Run EpiHiper
    do_run_epihiper

    # Compress the output files
    gzip -9 -f "$OUTPUT_DIR/output.csv"
    gzip -9 -f "$OUTPUT_DIR/outputSummary.csv"

    echo "Projection run completed successfully"
    exit 0
}
