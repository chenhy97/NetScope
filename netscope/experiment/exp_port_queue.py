from subprocess import Popen
import random
import os
import sys
import re
import time

from experiment import Experiment

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]

if True:
    abspath = os.path.abspath(__file__)
    while not abspath.endswith('netscope'):
        abspath = os.path.dirname(abspath)
    if abspath.endswith('netscope'):
        root_path = abspath
        print(root_path)
        sys.path.append(root_path)
        from analysis.load import Loader


class Exp(Experiment):

    def __init__(self):
        Experiment.__init__(self)

    def run(self):
        '''begin experiment'''
        MAX_QUEUE_RATE = 500
        quiet_time = 20
        interval = 0.1

        self.refresh_log_folder()
        # self.controller(volumn=20, data_from='hosts')
        self.controller(volumn=quiet_time / interval / 5,
                        sigma_num=50,
                        data_from='hosts')

        for sw in self.topo.get_switches():
            self.set_queue_rate(sw, MAX_QUEUE_RATE)

        self.send(interval)
        # self.send_pkt('h1', 'h4', msg="this_is_victim_flow",
        #               options=['--interval', str(interval)])
        self.sleep(quiet_time)  # basic prepare for ADR
        self.sleep(quiet_time)  # basic prepare for ADR
        self.sleep(10)

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
        rate = random.randint(3, 5)
        timeout = random.randint(20, 30)

        # Anoamly Inject
        inject_t = int(time.monotonic() * 1e8)  # inject timestamp
        self.set_queue_rate(culprit_sw, rate=rate, egress_port=port)
        self.sleep(timeout)

        # back to normals
        self.set_queue_rate(culprit_sw, rate=MAX_QUEUE_RATE, egress_port=port)
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
        # # end experiment
        self.kill("send")
        self.sleep(1)  # wait for pkts forwarding in network

        self.finish()
        self.save_log(EXP_KEY)
        self.wechat_bot(f"Finish: {EXP_KEY}")
        print(self.answer[EXP_KEY])


if __name__ == '__main__':
    exp = Exp()
    exp.run()
