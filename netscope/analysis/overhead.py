import sys
import numpy as np
from utils import load_collector, load_dst_hosts


def load_md():
    md_df = load_dst_hosts(log_dir='../host_log')
    content = ""
    for i, row in md_df.iterrows():
        content += f"{len(row['path'])},{row['latency']}\n"
    with open('data/INT-MD.csv', 'a') as f:
        f.write(content)


def load_mx():
    mx_df = load_collector(log_dir='../host_log')
    content = ""
    for i, row in mx_df.iterrows():
        content += f"{len(row['path'])},{row['latency']}\n"
    with open('data/INT-MX.csv', 'a') as f:
        f.write(content)


int_type = sys.argv[1]
if int_type == 'md':
    load_md()
elif int_type == 'mx':
    load_mx()
