# Run EpiHiper in Calibration Mode

do_run_epihiper_calib_estimate_R () {
    set -Eeuo pipefail

    # Inputs to be passed in via env variables
    echo "SYNPOP=$SYNPOP"
    echo "MULTIPLIER=$MULTIPLIER"
    echo "CELL_CONFIG_DIR=$CELL_CONFIG_DIR"
    echo "BASE_DISEASE_MODEL_FILE=$BASE_DISEASE_MODEL_FILE"
    echo "TRANSMISSIBILITY=$TRANSMISSIBILITY"
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
    "$PYTHON_EXE" "$CODE_DIR/epihiper_setup_calib.py" \
        --contact-network-file "$PARTITION_CACHE_DIR/$SYNPOP/$MULTIPLIER"/contact_network.txt \
        --persontrait-file "$SYNPOP_ROOT/$SYNPOP"/*_persontrait_epihiper.txt \
        --cell-config-directory "$CELL_CONFIG_DIR" \
        --base-disease-model-file "$BASE_DISEASE_MODEL_FILE" \
        --transmissibility $TRANSMISSIBILITY \
        --db-host "$DB_HOST" \
        --replicate "$REPLICATE" \
        --log-level "$EPIHIPER_LOG_LEVEL" \
        --output-directory "$OUTPUT_DIR"

    # Run EpiHiper
    do_run_epihiper

    # Compress the output files
    gzip -9 -f "$OUTPUT_DIR/output.csv"
    gzip -9 -f "$OUTPUT_DIR/outputSummary.csv"

    # Estimate R
    "$RSCRIPT_EXE" "$CODE_DIR/R_estimate.R" "$OUTPUT_DIR/output.csv.gz" > "$OUTPUT_DIR/estimated_R.txt"

    echo "Calibration run completed successfully"
    exit 0
}

do_run_epihiper_calib_fitting_error () {
    set -Eeuo pipefail

    # Inputs to be passed in via env variables
    echo "SYNPOP=$SYNPOP"
    echo "MULTIPLIER=$MULTIPLIER"
    echo "CELL_CONFIG_DIR=$CELL_CONFIG_DIR"
    echo "BASE_DISEASE_MODEL_FILE=$BASE_DISEASE_MODEL_FILE"
    echo "TRANSMISSIBILITY=$TRANSMISSIBILITY"
    echo "REPLICATE=$REPLICATE"
    echo "CALIBRATION_CONFIG_FILE=$CALIBRATION_CONFIG_FILE"
    echo "CALIBRATION_DATA_FILE=$CALIBRATION_DATA_FILE"
    echo "LOCATION=$LOCATION"
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
    "$PYTHON_EXE" "$CODE_DIR/epihiper_setup_calib.py" \
        --contact-network-file "$PARTITION_CACHE_DIR/$SYNPOP/$MULTIPLIER"/contact_network.txt \
        --persontrait-file "$SYNPOP_ROOT/$SYNPOP"/*_persontrait_epihiper.txt \
        --cell-config-directory "$CELL_CONFIG_DIR" \
        --base-disease-model-file "$BASE_DISEASE_MODEL_FILE" \
        --transmissibility $TRANSMISSIBILITY \
        --db-host "$DB_HOST" \
        --replicate "$REPLICATE" \
        --log-level "$EPIHIPER_LOG_LEVEL" \
        --output-directory "$OUTPUT_DIR"

    # Run EpiHiper
    do_run_epihiper

    # Compress the output files
    gzip -9 -f "$OUTPUT_DIR/output.csv"
    gzip -9 -f "$OUTPUT_DIR/outputSummary.csv"

    # Estimate fitting error
    "$RSCRIPT_EXE" "$CODE_DIR/fitting_error.R" \
        "$CALIBRATION_CONFIG_FILE" \
        "$OUTPUT_DIR/outputSummary.csv.gz" \
        "$CALIBRATION_DATA_FILE" \
        "$LOCATION" > "$OUTPUT_DIR/fitting_error.txt"

    echo "Calibration run completed successfully"
    exit 0
}

