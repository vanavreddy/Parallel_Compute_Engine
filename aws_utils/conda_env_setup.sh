#!/bin/bash

cd /home/ubuntu

echo "Downloading Miniconda ..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 
if [[ $done == 0 ]]; then
        echo "Done"
fi
sleep 2

echo "Installing miniconda..."
bash /home/ubuntu/Miniconda3-latest-Linux-x86_64.sh -b -p /home/ubuntu/miniconda3 >> /home/ubuntu/output_conda.txt 2>&1
if [[ $done == 0 ]]; then
	echo "Done"
fi
sleep 2

export PATH=$PATH:/home/ubuntu/miniconda3/bin
source activate base
conda --version 
source ~/.bashrc
sleep 2

echo "Clone repo..."
git clone https://github.com/vanavreddy/Parallel_Compute_Engine.git
if [[ $done == 0 ]]; then
	echo "Done"
fi
sleep 2

echo "Change permissions on the repo..."
chmod -R ugo+twx /home/ubuntu/Parallel_Compute_Engine
if [[ $done == 0 ]]; then
	echo "Done"
fi
sleep 2

# Create the Conda environments

cd /home/ubuntu/Parallel_Compute_Engine
echo "Creating py_env..."
conda env create -f conda_env_files/py_env.yml >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done"
fi

echo "Creating r_env..."
conda env create -f conda_env_files/r_env.yml >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done"
fi

echo "Creating node_env..."
conda env create -f conda_env_files/node_env.yml >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done"
fi

echo "Creating pg_env..."
conda env create -f conda_env_files/pg_env.yml >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done"
fi

source activate base

# Install pydantic version 1.10

conda activate py_env
pip install -U pydantic==1.10 >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing python packages"
fi
conda deactivate

sleep 5

# Install Node dependencies in node_env

conda activate node_env
npm install -g  @shoops/epi-hiper-validator >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing node packages"
fi
conda deactivate

sleep 5

# Install R dependencies in R_env (this step may take a few minutes)

conda activate r_env
Rscript -e 'install.packages(c("R.utils"), repos="http://cran.r-project.org")' >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing R.utils packages"
fi
sleep 5
Rscript -e 'install.packages(c("data.table"), repos="http://cran.r-project.org")' >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing data.table packages"
fi
sleep 5
Rscript -e 'install.packages(c("EpiEstim"), repos="http://cran.r-project.org")' >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing EpiEstim R packages"
fi
sleep 5
Rscript -e 'install.packages(c("jsonlite"), repos="http://cran.r-project.org")' >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing jsonlite R packages"
fi
sleep 5
Rscript -e 'install.packages(c("bit64"), repos="http://cran.r-project.org")' >> /home/ubuntu/output_conda.txt 2>&1
done=$?
if [[ $done == 0 ]]; then
	echo "Done installing bit64 R packages"
fi
conda deactivate

chmod -R ugo+rwx *

echo "Done conda env setup"

