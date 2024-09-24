#!/bin/bash

cd /home/ubuntu
echo "Cloning git repo..."
git clone https://github.com/vanavreddy/Parallel_Compute_Engine.git >> setup_out.txt 2>&1
if [[ $done == 0 ]]; then
        echo "Done"
fi

echo "Changing permissions on the repo..."
chmod -R ugo+twx /home/ubuntu/Parallel_Compute_Engine >> setup_out.txt 2>&1
if [[ $done == 0 ]]; then
        echo "Done"
fi

echo "Downloading Miniconda ..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh >> setup_out.txt 2>&1
if [[ $done == 0 ]]; then
        echo "Done"
fi

echo "Changing permissions on /home/ubuntu/* ..."
sudo chmod -R ugo+rwx *
if [[ $done == 0 ]]; then
        echo "Done"
fi
