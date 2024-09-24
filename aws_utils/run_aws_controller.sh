#!/bin/bash

cd /home/ubuntu/Parallel_Compute_Engine/aws_utils

echo "Exporting conda paths"
export PATH=$PATH:/home/ubuntu/miniconda3/bin
source activate base
conda activate py_env

echo "Setting controller details"
. export.sh

mkdir -p $PIPELINE_ROOT/controller_setup_root
#mkdir -p /home/ubuntu/epihiper-setup-logs/2023-12-05/controller_setup_root
cp /home/ubuntu/common* /home/ubuntu/epihiper-setup-logs/2023-12-05/

cd /home/ubuntu/Parallel_Compute_Engine/mackenzie
export PATH=$PATH:/home/ubuntu/.local/bin/
pip install -e .

sleep 30

which mackenzie

ls /home/ubuntu/.local/bin/mackenzie

nohup python /home/ubuntu/.local/bin/mackenzie controller 2>&1 | tee -a /home/ubuntu/controller.out &
