#!/bin/bash  
set -x
  
for i in $(seq 1 20)
do
    tcpprep -a client -i /mnt/netscope/DataSet/univ1/univ1_pt${i} -o /mnt/netscope/DataSet/univ1/cache/uv1_pt${i}_client.cache
done