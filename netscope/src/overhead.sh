#!/bin/bash

cd ..
python ./routing-controller.py

for i in $(seq 2 10) 
do   
sudo python ./experiment.py $i
cd analysis
python3 overhead.py md
cd ..
done  