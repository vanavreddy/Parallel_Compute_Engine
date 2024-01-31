#!/bin/bash
# shellcheck shell=bash disable=SC2034,SC2155
# MacKenzie/EpiHiperSetupUtils Pipeline Entry Point

# Path to the current script.
# Note when this script is submitted to slurm,
# Slurm will make a copy and put it in some some other place.
# So do not use this variable when running via slurm.
CUR_SCRIPT="$(realpath "${BASH_SOURCE[0]}")"

# Source the environment
. "../environment.sh"
export PYTHONPATH

cmd_make_pipeline_root () {
    set -Eeuo pipefail

    if [[ -e "$PIPELINE_ROOT" ]] ; then
        echo "This will remove '$PIPELINE_ROOT' and reecreate it"
        read -p "Are you sure? (press 'y' to continue): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]] ; then
            return
        fi

        set -x
        rm -rf "$PIPELINE_ROOT"
    fi

    set -x

    mkdir -p "$PIPELINE_ROOT"
    mkdir "$PIPELINE_ROOT/controller_setup_root"
    mkdir "$PIPELINE_ROOT/agent_setup_root"
    mkdir "$PIPELINE_ROOT/output_root"
    mkdir "$PIPELINE_ROOT/csmts_work_dir"
    mkdir "$PIPELINE_ROOT/bots_work_dir"
    mkdir "$PIPELINE_ROOT/logs"

    cd "$PIPELINE_ROOT"

    "$PY_CONDA_ENV/bin/mackenzie" makecert common
}

cmd_run_synpop_db () {
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

cmd_submit_synpop_db () {
    set -Eeuo pipefail
    set -x

    sbatch $PIPELINE_SBATCH_ARGS \
        --job-name synpop_db \
        --nodes 1 \
        --ntasks-per-node 1 \
        --cpus-per-task ${CPU_PER_NODE} \
        --partition ${PARTITION} \
        --time 1-00:00:00 \
        --output "$PIPELINE_ROOT/logs/%x-%j.out" \
        "$CUR_SCRIPT" run_synpop_db
}

cmd_run_controller () {
    set -Eeuo pipefail
    set -x

    # Save the ip of the ib0
    ip addr show dev ib0 | awk '/inet/ {print $2}' | cut -d / -f 1 | head -n 1 > "$CONTROLLER_HOST_FILE"

    export CONTROLLER_KEY_FILE="$PIPELINE_ROOT/common.key"
    export CONTROLLER_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export CONTROLLER_SETUP_ROOT="$PIPELINE_ROOT/controller_setup_root"
    export CONTROLLER_TASK_TIMEOUT="$TASK_TIMEOUT"
    export CONTROLLER_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export CONTROLLER_CONTROLLER_PORT=$CONTROLLER_PORT

    exec "$PY_CONDA_ENV/bin/mackenzie" controller
}

cmd_submit_controller () {
    set -Eeuo pipefail
    set -x

    sbatch $PIPELINE_SBATCH_ARGS \
        --job-name mackenzie:controller \
        --nodes 1 \
        --ntasks-per-node 1 \
        --cpus-per-task 2 \
        --partition ${PARTITION} \
        --time 1-00:00:00 \
        --output "$PIPELINE_ROOT/logs/%x-%j.out" \
        "$CUR_SCRIPT" run_controller
}

cmd_run_agent () {
    set -Eeuo pipefail
    set -x

    export AGENT_KEY_FILE="$PIPELINE_ROOT/common.key"
    export AGENT_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export AGENT_SETUP_ROOT="$PIPELINE_ROOT/agent_setup_root"
    export AGENT_CLUSTER="$CLUSTER"
    export AGENT_MAX_LOAD=$(( MAX_COMPUTE_NODES * CPU_PER_NODE / CPU_PER_TASK - PIPELINE_TASKS ))
    export AGENT_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export AGENT_CONTROLLER_PORT=$CONTROLLER_PORT

    exec "$PY_CONDA_ENV/bin/epihiper-setup-utils" mackenzie-agent \
        --env-file "../environment.sh" \
        --output-root "$PIPELINE_ROOT/output_root"
}

cmd_submit_agent () {
    set -Eeuo pipefail
    set -x

    sbatch $PIPELINE_SBATCH_ARGS \
        --job-name epihiper-pipeline:mackenzie-agent \
        --nodes 1 \
        --ntasks-per-node 1 \
        --cpus-per-task 2 \
        --partition ${PARTITION} \
        --time 1-00:00:00 \
        --output "$PIPELINE_ROOT/logs/%x-%j.out" \
        "$CUR_SCRIPT" run_agent
}

cmd_add_setup () {
    set -Eeuo pipefail
    set -x

    export CMD_KEY_FILE="$PIPELINE_ROOT/common.key"
    export CMD_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export CMD_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export CMD_CONTROLLER_PORT=$CONTROLLER_PORT

    exec "$PY_CONDA_ENV/bin/mackenzie" add-setup --setup-dir "$SETUP_DIR"
}

cmd_run_csm_task_source () {
    set -Eeuo pipefail
    set -x

    export CSMTS_KEY_FILE="$PIPELINE_ROOT/common.key"
    export CSMTS_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export CSMTS_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export CSMTS_CONTROLLER_PORT=$CONTROLLER_PORT

    export CSMTS_WORK_DIR="$PIPELINE_ROOT/csmts_work_dir"

    export CSMTS_RUN_NAME="test1"
    export CSMTS_SETUP_DIR="$SETUP_DIR"
    export CSMTS_NUM_REPLICATES=10
    export CSMTS_MULTIPLIER="$MULTIPLIER"
    export CSMTS_MAX_RUNTIME="$MAX_RUNTIME"

    export CSMTS_MAX_EVALS=50
    export CSMTS_N_ITER_NO_CHANGE=5
    export CSMTS_MIN_REL_IMPROVEMENT=0.01
    export CSMTS_MAKE_Y_POSITIVE=0

    exec "$PY_CONDA_ENV/bin/epihiper-setup-utils" csm-task-source
}

cmd_submit_csm_task_source () {
    set -Eeuo pipefail
    set -x

    sbatch $PIPELINE_SBATCH_ARGS \
        --job-name epihiper-pipeline:csm-task-source \
        --nodes 1 \
        --ntasks-per-node 1 \
        --cpus-per-task 2 \
        --partition ${PARTITION} \
        --time 1-00:00:00 \
        --output "$PIPELINE_ROOT/logs/%x-%j.out" \
        "$CUR_SCRIPT" run_csm_task_source
}

cmd_run_bayes_opt_task_source () {
    set -Eeuo pipefail
    set -x

    export BOTS_KEY_FILE="$PIPELINE_ROOT/common.key"
    export BOTS_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export BOTS_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export BOTS_CONTROLLER_PORT=$CONTROLLER_PORT

    export BOTS_WORK_DIR="$PIPELINE_ROOT/bots_work_dir"

    export BOTS_RUN_NAME="test1"
    export BOTS_SETUP_DIR="$SETUP_DIR"
    export BOTS_MULTIPLIER="$MULTIPLIER"
    export BOTS_MAX_RUNTIME="$MAX_RUNTIME"

    export BOTS_INIT_EVALS=64
    export BOTS_EXPLORE_EVALS=128
    export BOTS_EXPLOIT_EVALS=32
    export BOTS_PARALLEL_EVALS=10
    export BOTS_KAPPA_INITIAL=2.576
    export BOTS_KAPPA_SCALE=0.95

    exec "$PY_CONDA_ENV/bin/epihiper-setup-utils" bayes-opt-task-source
}

cmd_submit_bots_task_source () {
    set -Eeuo pipefail
    set -x

    sbatch $PIPELINE_SBATCH_ARGS \
        --job-name epihiper-pipeline:bots-task-source \
        --nodes 1 \
        --ntasks-per-node 1 \
        --cpus-per-task 2 \
        --partition ${PARTITION} \
        --time 1-00:00:00 \
        --output "$PIPELINE_ROOT/logs/%x-%j.out" \
        "$CUR_SCRIPT" run_bayes_opt_task_source
}

cmd_add_post_opt_tasks () {
    set -Eeuo pipefail
    set -x

    export POTS_KEY_FILE="$PIPELINE_ROOT/common.key"
    export POTS_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export POTS_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export POTS_CONTROLLER_PORT=$CONTROLLER_PORT

    export POTS_RUN_NAME="test1"
    export POTS_SETUP_DIR="$SETUP_DIR"
    export POTS_MULTIPLIER="$MULTIPLIER"
    export POTS_MAX_RUNTIME="$MAX_RUNTIME"

    export POTS_NUM_EVALS=20
    export POTS_OPT_STATUS_FILE="$PIPELINE_ROOT/bots_work_dir/status.csv"

    exec "$PY_CONDA_ENV/bin/epihiper-setup-utils" post-opt-task-source
}

cmd_run_proj_task_source () {
    set -Eeuo pipefail
    set -x

    export PTS_KEY_FILE="$PIPELINE_ROOT/common.key"
    export PTS_CERT_FILE="$PIPELINE_ROOT/common.crt"
    export PTS_CONTROLLER_HOST=$(< "$CONTROLLER_HOST_FILE" )
    export PTS_CONTROLLER_PORT=$CONTROLLER_PORT

    export PTS_RUN_NAME="proj1"
    export PTS_SETUP_DIR="$SETUP_DIR"
    export PTS_MULTIPLIER="$MULTIPLIER"
    export PTS_MAX_RUNTIME="$MAX_RUNTIME"

    export PTS_START_BATCH=1
    export PTS_NUM_REPLICATES="[10]"

    exec "$PY_CONDA_ENV/bin/epihiper-setup-utils" proj-task-source
}

cmd_default () {

read -r -d '' SUBCOMMANDS <<'EOF'
make_pipeline_root
submit_synpop_db
submit_controller
submit_agent
add_setup
submit_csm_task_source
submit_bots_task_source
add_post_opt_tasks
run_proj_task_source
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
