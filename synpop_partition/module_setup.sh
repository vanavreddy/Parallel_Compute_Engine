# Load the modules

. /etc/profile
module load intel/18.0 intelmpi/18.0

MPI_LAUNCHER="srun-pmi2"

#EPIHIPER_BIN_DIR="${CACHE_ROOT}/EpiHiper-code/build-openmpi-gcc-with-lid/src"

do_run_epihiper_parition () {
    srun --mpi=pmi2 --ntasks "$SLURM_NTASKS" "$EPIHIPER_BIN_DIR/EpiHiperPartition" --config "$OUTPUT_DIR/config.json"
}

do_run_epihiper () {
    srun --mpi=pmi2 --ntasks "$SLURM_NTASKS" "$EPIHIPER_BIN_DIR/EpiHiper" --config "$OUTPUT_DIR/config.json"
}
