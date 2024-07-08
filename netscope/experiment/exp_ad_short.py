#!/usr/bin/env python3
from subprocess import Popen
import random
import os
import sys
import re
import shutil
import subprocess
import time
import json

if True:
    # sys.path.append(os.path.join(os.getcwd(), 'experiment'))
    from experiment import Experiment
    print(os.getcwd())
    sys.path.append(os.getcwd())
    from analysis.load import Loader

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]

from src.lamp.routing_controller import QUEUE_RATE

with open("experiment/batch/config.json", "r") as f:
    config = json.load(f)


class Exp(Experiment):

    def inject_anomaly(self):
        # # # abnormal
        while True:
            loader = Loader()
            hosts = loader.load_hosts()
            try:
                src, dst = random.choice(self.send_list)
                paths = self.topo.get_shortest_paths_between_nodes(src, dst)
                path = random.choice(paths)  # [1:-2]
                hop_id = random.randint(1, len(path) - 2 - 1)
                port = self.topo.node_to_node_port_num(path[hop_id],
                                                       path[hop_id + 1])

                culprit_sw = path[hop_id]
                groundTruth = path[hop_id] + ',' + path[hop_id + 1] + ','
                if len(hosts[hosts.path_str.str.contains(groundTruth)]) == 0:
                    print(f"{groundTruth} failed")
                    continue
                break
            except:
                continue
        flow_num = len(self.send_list)
        rate = random.randint(int(flow_num / 2), flow_num)
        # rate = random.randint(100, 150)
        rate = 1
        # timeout = random.randint(1, 5)
        timeout = 0.5

        # Anoamly Inject
        inject_t = int(time.monotonic() * 1e8)  # inject timestamp
        self.set_queue_rate(culprit_sw, rate=rate, egress_port=port)
        self.sleep(timeout)

        # back to normals
        self.set_queue_rate(culprit_sw, rate=QUEUE_RATE, egress_port=port)
        self.sleep(10)

        self.answer[EXP_KEY].append(
            dict(src=src,
                 dst=dst,
                 paths=[','.join(p[1:-1]) + ',' for p in paths],
                 rate=rate,
                 port=port,
                 inject_t=inject_t,
                 timeout=timeout,
                 groundTruth=path[hop_id] + "," + path[hop_id + 1] + ",",
                 abnormalKind='port queue rate'))

    def run(self):
        '''begin experiment'''
        quiet_time = 20
        interval = 0.2

        self.refresh_log_folder()
        # self.controller(volumn=50, data_from='hosts')
        self.controller(data_from='hosts',
                        update_type='short',
                        **config['controller'])

        self.sleep(1)
        self.send_list = [
            # ('h1', 'h7'),
            # ('h1', 'h6'),
            # ('h5', 'h7'),
            # ('h1', 'h4'),
            # ('h2', 'h4'),
            # ('h6', 'h4'),
        ]

        for src in self.hosts:
            dst = random.choice([h for h in self.hosts if h != src])
            self.send_list.append((src, dst))

        for src, dst in self.send_list:
            pt = random.randint(1, 20)
            self.tcpreplay_edit(src, dst, pt=pt, x=0.1)
        # self.tcpreplay_edit(src, dst, x=1, limit=1)
        # break
        print(self.send_list)

        # init sleep time
        self.sleep(config['time']['init'])
        # self.sleep(30)

        self.inject_anomaly()

        self.sleep(30)
        # self.sleep(30)

        # end experiment
        self.kill("send")

        self.finish()
        self.save_log(EXP_KEY)
        if sys.argv[1] != "batch":
            print(sys.argv[1])
            self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
