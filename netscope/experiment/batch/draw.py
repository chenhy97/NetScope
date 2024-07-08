from matplotlib import pyplot as plt
import os
import sys
import json
import math

abspath = os.path.abspath(__file__)

if not abspath.endswith('netscope'):
    root_path = os.path.dirname(os.path.dirname(os.path.dirname(abspath)))
    print(root_path)
    os.chdir(root_path)
    sys.path.append(root_path)
    from analysis.load import Loader

markers = (list('ov^<>12348sp*hH+xXDd|_.,') + [i for i in range(12)]) * 10

with open('./build/build.json', 'r') as f:
    build = json.load(f)
log_dir = os.path.join(build['data_path'])
print(log_dir)

loader = Loader(log_dir)
# digests = loader.load_digest()
hosts = loader.load_hosts(debug=True)
hosts = hosts[(hosts.timestamp > 0) & (hosts.latency < 1e10)]

fig, axes = plt.subplots(nrows=2,
                         ncols=1,
                         sharex=True,
                         sharey=True,
                         figsize=(12, 8))

x_key = 'arrive_t'
# x_key = 'timestamp'
path_count = len(hosts.whole_path.unique())
for i, path in enumerate(sorted(hosts.whole_path.unique())):
    hosts[hosts.whole_path == path].plot(x_key,
                                         'latency',
                                         ax=axes[0],
                                         label=path,
                                         alpha=0.3,
                                         lw=1,
                                         marker=markers[i],
                                         ls='')
    axes[0].set_title('host')
    axes[0].legend(ncol=math.ceil(path_count / 12))

import pandas as pd

reg = pd.read_csv(f"{log_dir}/mininet/reg.csv")
reg['arrive_t'] = reg['src_tstamp'] + reg['latency']

if len(reg) > 0:
    reg.plot('arrive_t', 'latency', ls='', marker='.', ax=axes[1])

plt.xlim(
    (hosts.arrive_t.min(), hosts.sort_values('arrive_t')[:-5].arrive_t.max()))

# if digests is None or len(digests) != 0:
#     for i, path in enumerate(sorted(digests.whole_path.unique())):
#         digests[digests.whole_path == path].plot(x_key,
#                                                  'latency',
#                                                  ax=axes[1],
#                                                  label=path,
#                                                  alpha=0.3,
#                                                  lw=1,
#                                                  marker=markers[i],
#                                                  ls='')
axes[1].set_title('register')
plt.ylabel('latency')
plt.xlabel(x_key)

plt.savefig(os.path.join(log_dir, 'traffic.png'))
