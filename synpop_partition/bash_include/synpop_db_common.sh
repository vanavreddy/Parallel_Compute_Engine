# Synpop database common

# Run the synpop database
do_run_synpop_db () {
    set -Eeuo pipefail
    set -x

    if [[ ! -d "$DB_CACHE_DIR/postgres" ]] ; then
        echo "Postgres database doesn't exist"
        exit 1
    fi

    # Save the ip of the ib0
    ip addr show dev ib0 | awk '/inet/ {print $2}' | cut -d / -f 1 | head -n 1 > "$DBHOST_IP_FILE"

    # Start the postgres db
    exec "$POSTGRES_EXE" -D "$DB_CACHE_DIR/postgres"
    exit 0
}

# Make the synpop us state db
do_make_synpop_db_usa () {
    set -Eeuo pipefail

    # Inputs to be passed in via env variables
    echo "SYNPOP_LIST_FILE=$SYNPOP_LIST_FILE"

    set -x

    # Create the the work directory
    if [[ -d "$DB_CACHE_DIR" ]] ; then
        rm -rf "$DB_CACHE_DIR"
    fi
    mkdir -p "$DB_CACHE_DIR"

    # Create the password file
    echo "$EPIHIPER_DB_PASS" > "$DB_CACHE_DIR/pass.txt"

    # Initialize the dbatabase directory
    "$INITDB_EXE" -D "$DB_CACHE_DIR/postgres" -U "$EPIHIPER_DB_USER" --pwfile "$DB_CACHE_DIR/pass.txt"

    # Copy over the optimized postgres config
    cp -f "$POSTGRES_CONFIG" "$DB_CACHE_DIR/postgres/postgresql.conf"
    cp -f "$PG_HBA_CONFIG" "$DB_CACHE_DIR/postgres/pg_hba.conf"

    # Start postgres in the background
    "$POSTGRES_EXE" -D "$DB_CACHE_DIR/postgres" &
    trap "kill -s TERM %1" EXIT

    # Wait for postgres to be available
    set +e
    while true ; do
        echo "\q" | "$PSQL_EXE" -h localhost -p 5432 -U "$EPIHIPER_DB_USER" postgres > /dev/null 2>&1
        if [[ $? -eq 0 ]] ; then
            break
        fi
        sleep 1
    done
    set -e

    # Create epihiper_db database
    "$CREATEDB_EXE" -h localhost -p 5432 -U "$EPIHIPER_DB_USER" "$EPIHIPER_DB"

    # Create the synthetic population prep directory
    mkdir -p "$DB_CACHE_DIR/synpop_prep"

    # Get the list of synthetic populations
    SYNPOPS=$(cat "$SYNPOP_LIST_FILE")

    # Start copying the data to the database
    for synpop in $SYNPOPS ; do
        "$PYTHON_EXE" "$CODE_DIR/epihiper_db_pg_copy.py" \
        --persontrait-file "$SYNPOP_ROOT/$synpop"/*_persontrait_epihiper.txt \
        --host localhost \
        --username "$EPIHIPER_DB_USER" \
        --password "$EPIHIPER_DB_PASS" \
        --database "$EPIHIPER_DB" \
        --work-dir "$DB_CACHE_DIR/synpop_prep"
    done

    # Send term signal to postgres
    kill -s TERM %1

    # Wait for postgres to finish
    wait
    exit 0
}

# Make the world synpop db
do_make_synpop_db_world () {
    set -Eeuo pipefail

    # Inputs to be passed in via env variables
    echo "SYNPOP_LIST_FILE=$SYNPOP_LIST_FILE"

    set -x

    # Create the the work directory
    if [[ -d "$DB_CACHE_DIR" ]] ; then
        rm -rf "$DB_CACHE_DIR"
    fi
    mkdir -p "$DB_CACHE_DIR"

    # Create the password file
    echo "$EPIHIPER_DB_PASS" > "$DB_CACHE_DIR/pass.txt"

    # Initialize the dbatabase directory
    "$INITDB_EXE" -D "$DB_CACHE_DIR/postgres" -U "$EPIHIPER_DB_USER" --pwfile "$DB_CACHE_DIR/pass.txt"

    # Copy over the optimized postgres config
    cp -f "$POSTGRES_CONFIG" "$DB_CACHE_DIR/postgres/postgresql.conf"
    cp -f "$PG_HBA_CONFIG" "$DB_CACHE_DIR/postgres/pg_hba.conf"

    # Start postgres in the background
    "$POSTGRES_EXE" -D "$DB_CACHE_DIR/postgres" &
    trap "kill -s TERM %1" EXIT

    # Wait for postgres to be available
    set +e
    while true ; do
        echo "\q" | "$PSQL_EXE" -h localhost -p 5432 -U "$EPIHIPER_DB_USER" postgres > /dev/null 2>&1
        if [[ $? -eq 0 ]] ; then
            break
        fi
        sleep 1
    done
    set -e

    # Create epihiper_db database
    "$CREATEDB_EXE" -h localhost -p 5432 -U "$EPIHIPER_DB_USER" "$EPIHIPER_DB"

    # Create the synthetic population prep directory
    mkdir -p "$DB_CACHE_DIR/synpop_prep"

    # Get the list of synthetic populations
    SYNPOPS=$(cat "$SYNPOP_LIST_FILE")

    # Start copying the data to the database
    for synpop in $SYNPOPS ; do
        "$PYTHON_EXE" "$CODE_DIR/epihiper_db_frictionless.py" \
        --persontrait-file "$SYNPOP_ROOT/$synpop"/*_persontrait_epihiper.txt \
        --host localhost \
        --username "$EPIHIPER_DB_USER" \
        --password "$EPIHIPER_DB_PASS" \
        --database "$EPIHIPER_DB" \
        --work-dir "$DB_CACHE_DIR/synpop_prep"
    done

    # Send term signal to postgres
    kill -s TERM %1

    # Wait for postgres to finish
    wait
    exit 0
}
