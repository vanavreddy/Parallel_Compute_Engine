# Rivanna Environment

CLUSTER="rivanna"

# ---- Env variables for make_partitions ---- #

CODE_DIR="${PWD}"
PYTHONPATH="${CODE_DIR}/py_modules"

POSTGRES_CONFIG="${CODE_DIR}/postgres_config/postgresql.${CLUSTER}.conf"
PG_HBA_CONFIG="${CODE_DIR}/postgres_config/pg_hba.conf"

SYNPOP_ROOT="/project/biocomplexity/nssac/EpiHiperSynPop/v1.9.0"

# ---- Env variables for make_partitions ---- #


# ---- Env variables for conda environments ---- #
PY_CONDA_ENV="${HOME}/miniconda3/envs/py_env"
PYTHON_EXE="${PY_CONDA_ENV}/bin/python"

PG_CONDA_ENV="${HOME}/miniconda3/envs/pg_env"
POSTGRES_EXE="${PG_CONDA_ENV}/bin/postgres"
INITDB_EXE="${PG_CONDA_ENV}/bin/initdb"
CREATEDB_EXE="${PG_CONDA_ENV}/bin/createdb"
PSQL_EXE="${PG_CONDA_ENV}/bin/psql"

R_CONDA_ENV="${HOME}/miniconda3/envs/r_env"
RSCRIPT_EXE="${R_CONDA_ENV}/bin/Rscript"

NODE_CONDA_ENV="${HOME}/miniconda3/envs/node_env"

# ---- Env variables for conda environments ---- #



# ---- Env variables for pipeline_cache ---- #

EPIHIPER_DB_USER="epihiper"
EPIHIPER_DB_PASS="epihiper"
EPIHIPER_DB="epihiper_db"

CACHE_ROOT="/scratch/vv3xu/pipeline_cache"
DB_CACHE_DIR="${CACHE_ROOT}/DBSnapshotCache/us_50_states"
PARTITION_CACHE_DIR="${CACHE_ROOT}/SynNetPartitionCache/us_50_states"
EPIHIPER_BIN_DIR="${CACHE_ROOT}/EpiHiper-code/build-openmpi-gcc-with-lid/src"

# ---- Env variables for pipeline_cache ---- #



# ---- Env variables for mackenzie ---- #

DBHOST_IP_FILE="${DB_CACHE_DIR}/dbhost_ip.txt"
EPIHIPER_LOG_LEVEL="warn"

FZF_CMD="$HOME/miniconda3/envs/py_env/bin/fzf"

# ---- Env variables for mackenzie ---- #

# ---- Env variables for setup_utils ---- #
PIPELINE_SBATCH_ARGS="--account nssac_covid19"
MAX_FAILS=1
MAX_RUNTIME="3:00:00"
TASK_TIMEOUT=54000
MAX_COMPUTE_NODES=10
MULTIPLIER=16

EXPERIMENT="2023-12-05"

PIPELINE_ROOT="${HOME}/calibration-bo/${EXPERIMENT}"
SETUP_DIR="/scratch/${USER}/calibration-setup-samples/${EXPERIMENT}"

CONTROLLER_HOST_FILE="$PIPELINE_ROOT/controller_ip.txt"
CONTROLLER_PORT=18001
FZF_CMD="${HOME}/miniconda3/envs/py_env/bin/fzf"
CPU_PER_NODE=37
CPU_PER_TASK=1
PIPELINE_TASKS=4

# ---- Env variables for setup_utils ---- #

