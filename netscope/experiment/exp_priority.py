from subprocess import Popen
import random
import os
import re
import shutil

from experiment import Experiment

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]


class Exp(Experiment):

    def run(self):
        '''begin experiment'''
        self.refresh_log_folder()
        self.receive()
        self.sleep(1)
        interval = 0.2
        # self.send(interval)
        size = 9000
        self.send_pkt(
            'h4',
            'h8',
            msg="this_is_victim_flow" +
            ''.join([random.choice(self.letters) for i in range(size)]),
            options=['--interval', str(interval)])
        self.sleep(30)  # basic prepare for ADR
        # self.sleep(20)

        # # inject abnormal
        priority_level = 1
        burst_count = random.randint(100, 250)
        # while True:
        #     print(self.hosts.keys())
        #     src = random.choice(self.hosts.keys())
        #     dst = random.choice(self.hosts.keys())
        #     if src != dst and (src, dst) not in self.send_list:
        #         culprit_src, culprit_dst = src, dst
        #         break
        self.set_queue_rate('s1', 1)  # , egress_port=1)
        self.set_queue_rate('s6', 200)
        culprit_src, culprit_dst = 'h4', 'h7'
        self.send_pkt(
            culprit_src,
            culprit_dst,
            msg="this_is_priority_flow" +
            ''.join([random.choice(self.letters) for i in range(size)]),
            #   options=['--priority', 1,
            #            '--burst', 200],
            options=['--priority', 7, '--interval', 0.1],
        )

        # save answer
        paths = self.topo.get_shortest_paths_between_nodes(
            culprit_src, culprit_dst)
        sw_src_dst = "{src}-{dst}".format(src=paths[0][1], dst=paths[0][-2])
        self.answer[EXP_KEY].append({
            'src':
            culprit_src,
            'dst':
            culprit_dst,
            'priority':
            priority_level,
            'groundTruth':
            sw_src_dst,
            'paths': [','.join(p[1:-1]) + ',' for p in paths],
            'abnormalKind':
            'flow'
        })
        self.sleep(40)

        # end experiment
        self.kill("send")
        # self.sleep(10)  # wait for pkts forwarding in network
        self.kill("receive")

        # Popen(['python3', './analysis/utils.py']).wait()

        self.save_log(EXP_KEY)


if __name__ == '__main__':
    exp = Exp()
    exp.run()
