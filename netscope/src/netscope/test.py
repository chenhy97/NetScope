#!/usr/bin/env python3
from subprocess import Popen
import random
import os
import sys
import re
import shutil
import subprocess
from subprocess import Popen
import time
import pandas as pd

if True:
    sys.path.append(os.path.join(os.getcwd(), 'experiment'))
    from experiment import Experiment
    sys.path.append(os.getcwd())
    from analysis.load import Loader
    QUEUE_RATE = 200

EXP_KEY = "test"


class Exp(Experiment):

    def inject_anomaly(self):
        # # # abnormal
        for k in range(10):
            try:
                lc = pd.read_csv("log/LC.csv")
                flow = random.choice(lc['flow'].unique())

                src_ip, dst_ip = flow.split("-")[:2]
                src, dst = self.ip2h(src_ip), self.ip2h(dst_ip)
                paths = self.topo.get_shortest_paths_between_nodes(src, dst)
                path = random.choice(paths)  # [1:-2]
                hop_id = 1
                # hop_id = random.randint(1, len(path) - 2 - 1)
                port = self.topo.node_to_node_port_num(path[hop_id],
                                                       path[hop_id + 1])

                culprit_sw = path[hop_id]
                groundTruth = path[hop_id] + ',' + path[hop_id + 1] + ','
                break
            except:
                self.sleep(5)
                continue

        if k >= 9:
            while True:
                loader = Loader()
                hosts = loader.load_hosts()
                try:
                    src, dst = random.choice(self.send_list)
                    paths = self.topo.get_shortest_paths_between_nodes(
                        src, dst)
                    path = random.choice(paths)  # [1:-2]
                    hop_id = random.randint(1, len(path) - 2 - 1)
                    port = self.topo.node_to_node_port_num(
                        path[hop_id], path[hop_id + 1])

                    culprit_sw = path[hop_id]
                    groundTruth = path[hop_id] + ',' + path[hop_id + 1] + ','
                    if len(hosts[hosts.path_str.str.contains(
                            groundTruth)]) == 0:
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
        print("exp file: ", __file__)
        quiet_time = 20
        interval = 0.2

        self.refresh_log_folder()
        # self.controller(volumn=50, data_from='hosts')
        self.controller(volumn=quiet_time / interval, data_from='hosts')

        self.sleep(1)
        self.send_list = [
            ('h1', 'h7'),
            ('h2', 'h4'),
            ('h3', 'h1'),
            # #   ('h4', 'h8'), ('h5', 'h1'), ('h6', 'h8'),
            # ('h7', 'h2'),
            # ('h8', 'h4')
        ]
        # self.send_list = [('h1', 'h3'), ('h2', 'h4'), ('h3', 'h2'),
        #                   ('h4', 'h3')]
        self.send(interval)
        # for src in self.hosts:
        #     dst = random.choice([h for h in self.hosts if h != src])
        #     self.send_list.append((src, dst))

        # for sw in self.topo.get_switches():
        #     self.set_queue_rate(sw, 220)

        # for src, dst in self.send_list:
        #     pt = random.randint(1, 20)
        #     self.tcpreplay_edit(src, dst, pt=pt, x=0.1)
        #     # self.tcpreplay_edit(src, dst, x=1, limit=1)
        #     # break
        print(self.send_list)
        self.sleep(10)
        print("~~")
        # print("inject fault")
        # self.inject_anomaly()

        self.sleep(10)
        print("~~")

        self.sleep(30)

        
        # self.sleep(quiet_time * 2)
        # self.sleep(30)
        # self.sleep(30)

        # # inject abnormal
        # burst_src, burst_dst = random.choice(self.send_list)
        # burst_src, burst_dst = 'h1', 'h7'
        # self.send_pkt(burst_src, burst_dst, options=['--interval', '0.01'])

        # self.tcpreplay_edit(
        #     burst_src,
        #     burst_dst,
        #     x=10000,
        #     duration=2,
        #     pcap_path=
        #     "/home/user/dds/netscope/resources/workloads/e2edelay/h1-h8.pcp")
        

        # w2 = 4
        # flow, entry = self.ECMP_imbalance(w1=1, w2=w2, flow=ei_flow)
        # self.sleep(10)
        # fork_ctrl = self.get_thrift_controllor(ei_fork)
        # fork_ctrl.table_modify("get_ECMP_weight", "set_ECMP_weights", entry,
        #                        ["1", "1"])
        # dst_sw = 6
        # fork_ctrl.register_write("MyIngress.ECMP_bit", dst_sw * 2 + 0, 0)
        # fork_ctrl.register_write("MyIngress.ECMP_bit", dst_sw * 2 + 1, 0)

        # # save answer
        # paths = self.topo.get_shortest_paths_between_nodes(
        #     burst_src, burst_dst)
        # sw_src_dst = "{src}-{dst}".format(src=paths[0][1], dst=paths[0][-2])
        # self.answer[EXP_KEY].append(
        #     dict(src=burst_src,
        #          dst=burst_dst,
        #          groundTruth=sw_src_dst,
        #          paths=[','.join(p[1:-1]) + ',' for p in paths],
        #          abnormalKind='flow'))
        # self.sleep(30)
        # self.sleep(30)
        # self.sleep(30)

        # end experiment
        self.kill("send")
        # self.sleep(10)  # wait for pkts forwarding in network

        self.finish()
        self.save_log(EXP_KEY)
        # self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
