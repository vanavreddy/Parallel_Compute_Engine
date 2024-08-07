#!/bin/bash


whoami

ssudo usermod -G root ubuntu

sudo usermod -g 0 ubuntu

useradd -m -G root ubuntu

su - ubuntu 

whoami

cd /home/ubuntu


git clone https://github.com/vanavreddy/Benchmarking_Calorimeter_Shower_Simulation_Generative_AI.git 
chmod -R ugo+twx /home/ubuntu/Benchmarking_Calorimeter_Shower_Simulation_Generative_AI 
curl icanhazip.com > /home/ubuntu/controller_ip.txt 
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 
#bash /home/ubuntu/Miniconda3-latest-Linux-x86_64.sh -b > out_miniconda.txt
#export PATH=$PATH:/opt/miniconda3:/opt/miniconda3/bin 
#conda --version >> /home/ubuntu/out_miniconda.txt

tar xvf /home/ubuntu/Unified_Epihiper_Pipeline_Setup.tar.gz

sudo chmod -R ugo+rwx *

sleep 10

# Create the Conda environments

#cd /home/ubuntu/Unified_Epihiper_Pipeline_Setup
#conda env create -f conda_env_files/py_env.yml
#conda env create -f conda_env_files/r_env.yml
#conda env create -f conda_env_files/node_env.yml
#conda env create -f conda_env_files/pg_env.yml

