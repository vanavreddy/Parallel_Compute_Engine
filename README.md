# Parallel Compute Engine - PaCE

PaCE is a multi-cluster HPC scheduling system used to execute US national-scale epidemic simulation models. PaCE can be setup in three different configuration. The three configurations are:
1. Single HPC cluster
2. Multiple HPC clusters with controller in AWS cloud instance
3. Multiple HPC cluster where the HPC cluster is in AWS cloud along with the controller running on AWS cloud instance.

The three configurations are dipicted in figure below.

![three configs](https://github.com/vanavreddy/Parallel_Compute_Engine/blob/master/three_configs.png?raw=true)

Utilities for setting up and running EpiHiper.

These are common steps to setup the pipeline, these steps are executed in all three configurations.  

1. Set up the conda environment
2. Set up the environment File
3. Install epihiper_setup_utils and mackenzie
4. Partition the networks
5. Start the pipeline

\* You may NOT need to execute all the steps every time. The list above shows steps for 
first time setup. 

Additional steps specific for a configuration are discussed later.

## 1. Set up the conda environment

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
    $ bash ./Miniconda3-latest-Linux-x86_64.sh
    
    # Follow the prompts. When asked "Do you wish to update your shell profile
    to automatically initialize conda?" Choose "yes".
   ```
For ARM architecture, download the installer from <a href=https://repo.anaconda.com/archive/Anaconda3-2024.06-1-Linux-aarch64.sh>here</a>.

Once setup is done, please ensure that your conda config contains the following:

   ```
    # cat ~/.condarc
 
      channels:
        - conda-forge
        - defaults
      anaconda_upload: false
      auto_activate_base: false
   ```
If the file is not created during install, create the file, copy the above text and 
paste it in ~/.condarc file. 

This pipeline assumes Python 3.11. Conda version < 4.11 may have issues with 
Python 3.11. Ensure that you have Conda version 4.11+ once installed.

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

    $ cd Unified_Epihiper_Pipeline_Setup
    $ conda env create -f conda_env_files/py_env.yml
    $ conda env create -f conda_env_files/r_env.yml
    $ conda env create -f conda_env_files/node_env.yml
    $ conda env create -f conda_env_files/pg_env.yml
     
    # Install pydantic version 1.10
     
    $ conda activate py_env
    $ pip install -U pydantic==1.10
    $ pip install boto3
    $ conda deactivate
     
    # Install R dependencies in R_env (this step may take a few minutes)
     
    $ conda activate r_env
    $ Rscript -e 'install.packages(c("R.utils", "data.table", "EpiEstim", "jsonlite", "bit64"), repos="http://cran.r-project.org")'
    $ conda deactivate
     
    # Install Node dependencies in node_env
  
    $ conda activate node_env
    $ npm install -g  @shoops/epi-hiper-validator
    $ conda deactivate
   ```

## 2. Set up the Environment file

On the top level of the directory, change the environment.sh file to reflect 
the local paths and slurm condiguration specific for that cluster, e.g., rivanna or anvil.
The changes may also include conda paths, path to pipeline cache 
directory and calibration setup files.

We have provided template environment files for specific clusters in the 
cluster_template_files directory. Copy the appropriate files to the top 
level and make changes as needed.

## 3. Install epihiper_setup_utils and mackenzie 

Install epihiper_setup_utils,

  ```
   $ conda activate py_env
   $ cd epihiper_setup_utils
   $ pip install -U -e .
   $ cd ../
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
1) EpiHiper source and build directories,
2) partitioned synthetic contact networks,
3) persontrait PostgreSQL database directories.

**Note: PostgreSQL requires the database directory
and all the files in that directory
are owned by the user running the PostgreSQL process.**

   ```
    # On Rivanna, the shared PIPELINE_CACHE directory is located at
    $ export PIPELINE_CACHE=/project/bii_nssac/COVID-19_USA_EpiHiper/pipeline_cache
    
    # On Anvil, the shared PIPELINE_CACHE directory is located at
    $ export PIPELINE_CACHE=$PROJECT/pipeline_cache
   ```
If you do not have permissions to access the files or directories in this path,
contact the group/owner of those direcoties.

Additionally, you can also create you own copy of the PIPELINE_CACHE and 
export the new location instead.

### 3.2 Compiling EpiHiper

We compile EpiHiper on every cluster with the cluster's optimized 
compiler and MPI implementation. EpiHiper is compiled with MPI and 
without OpenMP. We create two builds of EpiHiper, one with 
location ID support and one without location ID support. 

When running simulations using the detailed populations of the 50 US 
states, we use the build with location ID support. When running simulations 
using the coarse populations, we use the build without location ID support. 
This is to accomodate the differences in the underlying synthetic populations.

#### Compiling EpiHiper on Rivanna

On Rivanna we compile EpiHiper with Intel compilers and IntelMPI.
On Rivanna we use the cluster's CMake and PostgreSQL libraries.

```
  # Make sure PIPELINE_CACHE directory is set and created
  $ echo $PIPELINE_CACHE

  # Clone the EpiHiper-code and update the submodules
  $ cd $PIPELINE_CACHE
  $ git clone https://github.com/NSSAC/EpiHiper-code.git
  $ cd EpiHiper-code
  $ git submodule update --init

  # Allocate a node to compile Epihipe code (this is an interactive session)
  $ srun -A nssac_covid19 -p bii --nodes 1 --ntasks-per-node 1 --cpus-per-task 37 -W 0 --time 2:00:00 --pty $SHELL

  # Load the required modules
  $ module intel/18.0 intelmpi/18.0

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

  # Once compilation is complete, exit the interactive session to get back to head/login node
  $ exit
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

  # Once compilation is complete, exit the interactive session to get back to head/login node

  $ exit
```

## 4. Partitioning the networks
```
  # Modify the environment.sh file such that CACHE_ROOT, SYNPOP_ROOT, CODE_DIR, LOG_DIR and conda envs
 point to the correct filesystem paths on that cluster.

  $ cd Unified_Epihiper_Pipeline_Setup
  $ . environment.sh
  $ cd synpop_partition
  $ conda activate py_env
  $ python make_partitions.py
```
This may take several minutes for all the jobs to finish. To check the status of the slurm jobs, 
run 'squeue -u $USER' command.

## 5. Start the pipeline

Once the partition step finishes, cd back to epihiper-setup-utils and execute 
the following steps (replace <cluster_name> with rivanna, anvil or bridges).

```
  # change the environment.sh file to reflect file system paths on that specific cluster

  $ cd Unified_Epihiper_Pipeline_Setup
  $ conda activate py_env
  $ . environment.sh
  $ cd epihiper_setup_utils
  $ ./pipeline_main.sh
  
  # Runing this script displays options from which you can select to run different
  components and setup steps, using MacKenzie, to submit EpiHiper jobs.
  
  # The correct order to select from the displayed options is:
  # 1) make_pipeline_root -> This will create the necessary dictories.
  # 2) submit_synpop_db -> This will initialize the SynthPopDB databse.
  # 3) submit_controller -> This will start MacKenzie controller process on a compute node.
  # 4) start_aws_controller -> this will start an AWS EC2 instance and set the instance to run the controller.
  # 5) submit_agent -> This will start the agent. This step must be executed only after controller is started up.
  # 6) add_setup -> copies the required files.
  # 7) submit_bots_task_source -> this will start up bot which pulls ready tasks to execute on compute nodes.
```

## Configuration a: Single HPC cluster.

Simply run all the steps, 1 through 5. In step-5, select "submit_controller" option.

## Configuration b: Multiple HPC clusters with controller in AWS cloud instance.

Requirements: 

1. AWS admin account with permissions to create/delete resources.
2. Create and download a keypair using the steps [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html).Make sure you save your .pem file locally.
  

Run all the steps, 1 through 5 on the headnode on each of the HPC clusters. Additionally, you will need to install the following packages in your py_env created in step-1. 

Install Node Version Manager with the lastest Long-Term Support (TS) Node.js version.

```
$ conda install conda-forge::nodejs

$ curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
$ chmod ug+x ~/.nvm/nvm.sh
$ source ~/.nvm/nvm.sh
$ nvm install --lts
$ node --version
v20.15.1
```

Install AWS ParallelCluster packages
```
$ pip install aws-parallelcluster
```

Verify that AWS ParallelCluster is installed correctly.

```
$ pcluster version
{
  "version": "3.10.1"
}
```

To upgrade to the latest version of AWS ParallelCluster, run the installation command again.

```
$ pip install --upgrade aws-parallelcluster
```

Install the AWS Command Line Interface tools.

```
$ pip install awscli
```


In step-5, select "start_aws_controller" option. After the controller instance starts, SSH to the instance and run the controller.

```
# For example, after selecting the 'start_aws_controller', you will be promted to SSH to the instance.

$ ssh -i /home/vv3xu/calibration-bo/2023-12-05/aws_setup_root/controller_keypair.pem ubuntu@54.83.130.78

# The execute the script to start the controller process.

$ bash /home/ubuntu/Parallel_Compute_Engine/aws_utils/run_aws_controller.sh

```

Once the pipeline tasks complete, make sure you delete the AWS controller instance. 

```
$ cd aws_utils
$ python aws_delete_controller.py
```

## Configuration c: Multiple HPC cluster where the HPC cluster is in AWS cloud along with the controller running on AWS cloud instance.

First, create HPC cluster on AWS resources using CloudFormation stack.

```
$ cd aws_utils
$ python aws_create_cluster.py --key_name <name of the keypair> --stack_name <name of your choice> --instance_count <number of compute nodes>
```

SSH to headnode of the newly created HPC cluster on AWS resources. Run all the steps, 1 through 5 on the headnode of each of the HPC clusters. In step-5, select "start_aws_controller" option. Once the controller instance is ready, SSH to the AWS  controller installer and start the controller script. 

Once the pipeline tasks complete, make sure you delete the AWS HPC cluster and AWS controller instance. 

```
$ cd aws_utils
$ python aws_delete_controller.py
$ python aws_delete_cluster.py

python aws_delete_cluster.py
```
