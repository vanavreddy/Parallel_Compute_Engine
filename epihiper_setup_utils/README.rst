EpiHiper Setup Utilities
========================

Utilities for setting up and EpiHiper runs.

This document provides instructions for setting up EpiHiper Setup Utilities.

Setting up the Conda Environment
--------------------------------

We use Conda for managing software dependencies
other than EpiHiper, C++ compilers, and MPI implementations.
In particular conda environments are used for
Python, R, Node.js, PostgreSQL, and Cmake.

We expect that the user of the pipeline will install Miniconda
in their home directory on every compute cluster.

.. code:: bash

   # Download Latest Miniconda

   $ cd ~
   $ wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   $ sh ./Miniconda3-latest-Linux-x86_64.sh

   # Follow the prompts

Once setup is done, please ensure that your conda config contains the following:

.. code::

  # ~/.condarc

  channels:
    - conda-forge
    - defaults
  anaconda_upload: false
  auto_activate_base: false

This pipeline assumes we will be using Python 3.11.
Conda version < 4.11 have issues with Python 3.11.
Please ensure that you have Conda version 4.11+ once installed.

.. code:: bash

  $ conda --version
  conda 4.11.0

Pipeline Conda Environment
--------------------------

We create different conda environments to manage
Python, R, Node.js, and PostgreSQL.
Using different environments is necessary
as some of the packages conflict with each other.

Note: We also install cmake and tzdata in the postgres environment and fzf in the Python environment.

.. code:: bash

  # Create the Conda environments

  conda create -y -n py_env python=3.11 fzf
  conda create -y -n R_env r-essentials r-base=4.1.0
  conda create -y -n node_env nodejs=15
  conda create -y -n pg_env postgresql=11.4 cmake tzdata

  # Install pedantic version 1.10

  conda activate py_env
  pip install -U pydantic==1.10
  conda deactivate

  # Install R dependencies in R_env

  conda activate R_env
  Rscript -e 'install.packages(c("R.utils", "data.table", "EpiEstim", "jsonlite", "bit64"), repos="http://cran.r-project.org")'
  conda deactivate

  # Install Node dependencies in node_env

  conda activate node_env
  npm install -g  @shoops/epi-hiper-validator
  conda deactivate

Install epihiper_setup_utils
----------------------------
In the top directory of the git repository execute:

.. code:: bash

  conda activate py_env
  pip install .
  conda deactivate

