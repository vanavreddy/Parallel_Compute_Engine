#!/bin/bash

export PATH=$PATH:/home/ubuntu/miniconda3/bin
source activate base
conda activate py_env

cd Parallel_Compute_Engine/
. export.sh

mkdir /home/ubuntu/epihiper-setup-logs/2023-12-05/
cp ~/common* /home/ubuntu/epihiper-setup-logs/2023-12-05/

cd mackenzie
export PATh=$PATH:/home/ubuntu/.local/bin/
pip install -e .

python /home/ubuntu/.local/bin/mackenzie controller
