# EpiHiper Setup Utilities

Utilities for setting up and running EpiHiper.

There are multiple steps to setup different parts of the pipeline. One may not 
need to execute all the steps every time. The list below shows steps for for 
first time setup.

1. Set up the Conda environment
2. Set up the Environment File
3. Install epihiper_setup_utils and mackenzie
4. Partition the Networks
5. Start the Pipeline

## 1. Set up the Conda environment

We use Conda for managing software dependencies
other than EpiHiper, C++ compilers, and MPI implementations.
In particular, the conda environments are used for
Python, R, Node.js, PostgreSQL, and Cmake.

### 1.1 Install Miniconda
 
We expect that the user of the pipeline will install Miniconda
in their home directory on every compute cluster.

   ```
    # Download Latest Miniconda
    
    $ cd ~
    $ wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    $ sh ./Miniconda3-latest-Linux-x86_64.sh
    
    # Follow the prompts
   ```
Once setup is done, please ensure that your conda config contains the following:
   ```
    # ~/.condarc
 
      channels:
        - conda-forge
        - defaults
      anaconda_upload: false
      auto_activate_base: false
   ```

This pipeline assumes we will be using Python 3.11.
Conda version < 4.11 have issues with Python 3.11.
Please ensure that you have Conda version 4.11+ once installed.

   ```
    $ conda --version
    conda 4.11.0
   ```

### 1.2 Configure Conda Environments

We create different conda environments to manage
Python, R, Node.js, and PostgreSQL.
Using different environments is necessary
as some of the packages conflict with each other.

Note: We also install cmake and tzdata in the postgres environment 
and fzf in the Python environment.

   ```
    # Create the Conda environments
     
    conda env create -f conda_env_files/py_env.yml
    conda env create -f conda_env_files/r_env.yml
    conda env create -f conda_env_files/node_env.yml
    conda env create -f conda_env_files/pg_env.yml
     
    # Install pedantic version 1.10
     
    conda activate py_env
    pip install -U pydantic==1.10
    conda deactivate
     
    # Install R dependencies in R_env (this step may take a few minutes)
     
    conda activate r_env
    Rscript -e 'install.packages(c("R.utils", "data.table", "EpiEstim", "jsonlite", "bit64"), repos="http://cran.r-project.org")'
    conda deactivate
     
    # Install Node dependencies in node_env
  
    conda activate node_env
    npm install -g  @shoops/epi-hiper-validator
    conda deactivate
  
    # Install FZF fuzzy finder in the base conda environment
  
    conda install -n base fzf
   ```

## 2. Set up the Environment file

On the top level of the directory, change the environment.sh file to reflect the local paths and slurm condiguration specific for that cluster, e.g., rivanna or anvil. The changes may also include conda paths, path to pipeline cache directory and calibration setup files.

We have provided template environment files for specific clusters in the cluster_template_files directory. Copy the appropriate files to the top level and make changes as needed.

## 3. Install epihiper_setup_utils and mackenzie 

Install epihiper_setup_utils,

  ```
   $ conda activate py_env
   $ cd epihiper_setup_utils
   $ pip install -U -e .
  ```

Now, install the components in MacKenzie directory,

  ```
   $ cd mackenzie
   $ pip install -U -e .
   $ conda deactivate
  ```

### 3.1 Setting Up Pipeline Cache Directory

We need to define pipeline cache directory on each cluster.
This directory must store:
the EpiHiper source and build directories,
the partitioned synthetic contact networks,
and persontrait PostgreSQL database directories.

Note that PostgreSQL required the database directory
and all the files underneath it
are owned by the same user as the one running the PostgreSQL process.

   ```
    # On Rivanna
    $ export PIPELINE_CACHE=/project/bii_nssac/COVID-19_USA_EpiHiper/pipeline_cache
    
    # On Anvil
    $ export PIPELINE_CACHE=$PROJECT/pipeline_cache
   ```

### 3.2 Compiling EpiHiper

We compile EpiHiper on every cluster
with the cluster's optimized compiler and MPI implementation.
EpiHiper is compiled with MPI and without OpenMP.
We also create two builds of EpiHiper one with location ID support
and one without location ID support.
When running simulations using the detailed populations of the 50 US states
we use the build with location ID support.
When running simulations using the coarse populations
we use the build without location ID support.
These are due to the differences in the underlying synthetic populations.

#### Compiling EpiHiper on Rivanna

On Rivanna we compile EpiHiper with Intel compilers and IntelMPI.
On Rivanna we use the cluster's CMake and PostgreSQL libraries.

```
  # Make sure PIPELINE_CACHE directory is set and created
  $ echo $PIPELINE_CACHE

  # Clone the EpiHiper-code and update the submodules
  $ cd $PIPELINE_CACHE
  $ git clone git@github.com:NSSAC/EpiHiper-code.git
  $ cd EpiHiper-code
  $ git submodule update --init

  # Allocate a node to compile stuff
  $ srun -A nssac_covid19 -p bii --nodes 1 --ntasks-per-node 1 --cpus-per-task 40 -W 0 --time 2:00:00 --pty $SHELL

  # Load the required modules
  $ module load git/2.4.1 intel/18.0 intelmpi/18.0 cmake/3.12.3 python/3.6.6
  $ export CC=icc
  $ export CXX=icpc

  # Create the build with location ID

  $ mkdir $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-with-lid
  $ cd $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-with-lid
  $ cmake .. -DENABLE_LOCATION_ID=ON -DENABLE_MPI=ON -DENABLE_OMP=OFF -DCMAKE_BUILD_TYPE=Release
  $ make -j 64

  # Create the build with location ID

  $ mkdir $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-without-lid
  $ cd $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-without-lid
  $ cmake .. -DENABLE_LOCATION_ID=OFF -DENABLE_MPI=ON -DENABLE_OMP=OFF -DCMAKE_BUILD_TYPE=Release
  $ make -j 64
```

#### Compiling EpiHiper on Anvil

On Anvil we compile EpiHiper with GCC compilers and OpenMPI.
We get postgres and cmake from using a conda environment.
Cmake needs to come from the conda environment
so that cmake can find the conda environment's postgres installation.

```
  # Make sure PIPELINE_CACHE directory is set and created
  $ echo $PIPELINE_CACHE

  # Clone the EpiHiper-code and update the submodules
  $ cd $PIPELINE_CACHE
  $ git clone git@github.com:NSSAC/EpiHiper-code.git
  $ cd EpiHiper-code
  $ git submodule update --init

  # Allocate a node to compile stuff
  $ srun -A bio220016  -p standard --nodes 1 --ntasks-per-node 1 --cpus-per-task 128 -W 0 -t 6:00:00 --pty /bin/bash

  # Load the required modules and conda env
  # We get postgres and cmake from conda pg_env
  $ module load gcc/11.2.0 openmpi/4.0.6 python/3.9.5
  $ conda activate pg_env

  # Create the build with location ID

  $ mkdir $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-with-lid
  $ cd $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-with-lid
  $ cmake .. -DENABLE_LOCATION_ID=ON -DENABLE_MPI=ON -DENABLE_OMP=OFF -DCMAKE_BUILD_TYPE=Release
  $ make -j 64

  # Create the build with location ID

  $ mkdir $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-without-lid
  $ cd $PIPELINE_CACHE/EpiHiper-code/build-openmpi-gcc-without-lid
  $ cmake .. -DENABLE_LOCATION_ID=OFF -DENABLE_MPI=ON -DENABLE_OMP=OFF -DCMAKE_BUILD_TYPE=Release
  $ make -j 64
```

## 4. Partitioning the networks
```
  # Modify the environment.sh file such that SYNPOP_ROOT and FZF_CMD
 point to the correct filesystem paths on that cluster.

  $ . environment.sh
  $ cd synpop_partition
  $ conda activate py_env
  $ python make_partitions.py
```

## 5. Start the pipeline

Once this step finishes, cd back to epihiper-setup-utils and execute 
the following steps (replace <cluster_name> with rivanna, anvil or bridges).

```
  # change the environment.sh file to reflect file system paths on that specific cluster
  
  $ . environment.sh
  
  $ cd epihiper-setup-utils
  
  $ conda activate py_env
  
  $ ./pipeline_main.sh
  
  # Runing this script displays options from which you can select to run different
  components and setup steps, using MacKenzie, to submit EpiHiper jobs.
  
  # The correct order to select from the displayed options is:
  # 1) make_pipeline_root -> This will create the necessary dictories.
  # 2) submit_synpop_db -> This will initialize the SynthPopDB databse.
  # 3) submit_controller -> This will start MacKenzie controller process on a compute node.
  # 4) submit_agent -> This will start the agent. This step must be executed only after controller is started up.
  # 5) add_setup ->
  # 6) submit_bots_task_source -> this will start up bot which pulls ready tasks to execute on compute nodes

```
