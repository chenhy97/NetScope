#!/usr/bin/env python3
from subprocess import Popen
import random
import re

from experiment import Experiment

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]


class Exp(Experiment):
    def __init__(self):
        self.send_list = [
            ('h1', 'h7'),
            ('h2', 'h4'),
            ('h3', 'h1'),
            ('h4', 'h8'),
            ('h5', 'h1'),
            ('h6', 'h8'),
            #   ('h7', 'h2'), ('h8', 'h4')
        ]
    def run(self):
        '''begin experiment'''
        quiet_time = 20
        interval = 0.2

        self.refresh_log_folder()
        # self.controller(volumn=50, data_from='hosts')
        self.controller(volumn=quiet_time / interval, data_from='hosts')

        self.sleep(1)
        
        # self.send_list = [('h1', 'h3'), ('h2', 'h4'), ('h3', 'h2'),
        #                   ('h4', 'h3')]
        # self.send(interval)
        # for src in self.hosts:
        #     dst = random.choice([h for h in self.hosts if h != src])
        #     self.send_list.append((src, dst))

        for src, dst in self.send_list:
            pt = random.randint(1, 20)
            self.tcpreplay_edit(src, dst, pt=pt, x=0.01)
            # self.tcpreplay_edit(src, dst, x=1, limit=1)
            # break
        print(self.send_list)

        self.sleep(quiet_time)  # basic prepare for ADR
        self.sleep(quiet_time * 2)
        # self.sleep(30)
        # self.sleep(30)

        # # inject abnormal
        burst_src, burst_dst = random.choice(self.send_list)
        # burst_src, burst_dst = 'h1', 'h7'
        self.tcpreplay_edit(burst_src,
                            burst_dst,
                            x=10000,
                            duration=2,
                            pcap_path="/mnt/netscope/DataSet/univ1/univ1_pt20")

        # save answer
        paths = self.topo.get_shortest_paths_between_nodes(
            burst_src, burst_dst)
        sw_src_dst = "{src}-{dst}".format(src=paths[0][1], dst=paths[0][-2])
        self.answer[EXP_KEY].append(
            dict(src=burst_src,
                 dst=burst_dst,
                 groundTruth=sw_src_dst,
                 paths=[','.join(p[1:-1]) + ',' for p in paths],
                 abnormalKind='flow'))
        self.sleep(10)
        self.sleep(30)
        # self.sleep(30)

        # end experiment
        self.kill("send")
        # self.sleep(10)  # wait for pkts forwarding in network

        self.finish()
        self.save_log(EXP_KEY)
        self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
