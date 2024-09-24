#!/bin/bash

export PATH=$PATH:/home/ubuntu/miniconda3/bin
source activate base
conda activate py_env

. export.sh

mkdir -p $PIPELINE_ROOT/controller_setup_root
#mkdir -p /home/ubuntu/epihiper-setup-logs/2023-12-05/controller_setup_root
cp ~/common* /home/ubuntu/epihiper-setup-logs/2023-12-05/

cd ../mackenzie
export PATH=$PATH:/home/ubuntu/.local/bin/
pip install -e .

nohup python /home/ubuntu/.local/bin/mackenzie controller 2>&1 | tee -a controller.out &
