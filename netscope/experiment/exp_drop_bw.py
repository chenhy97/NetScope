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
        quiet_time = 20
        interval = 0.1

        self.refresh_log_folder()
        self.controller(volumn=20, data_from='hosts')
        # self.controller(volumn=quiet_time/interval, data_from='hosts')

        self.sleep(1)
        self.send(interval, msg_size=(0, 100))

        # self.send_pkt('h1', 'h4', msg="this_is_victim_flow",
        #               options=['--interval', str(interval),
        #                        #    '--times', '1'
        #                        ]
        #               )
        self.sleep(quiet_time)  # basic prepare for ADR
        # self.sleep(quiet_time*2)
        # self.sleep(10)

        # # inject abnormal
        src, dst = random.choice(self.send_list)
        # burst_count = 200
        elephant_count = random.randint(20, 25)
        # elephant_interval = (random.random() + 1)/10

        msg = "this_is_culprit_flow" + ''.join([
            random.choice(self.letters)
            for _ in range(random.randint(500, 800))
        ])

        bandwidth = 1
        elephant_interval = 1 / (bandwidth / (len(msg) / 1024))

        times = 5
        elephant_count = 5 / elephant_interval * times
        self.send_pkt(src,
                      dst,
                      msg=msg,
                      options=[
                          '--interval', elephant_interval, '--times', times,
                          '--max_count', elephant_count
                      ])

        # save answer
        paths = self.topo.get_shortest_paths_between_nodes(src, dst)
        sw_src_dst = "{src}-{dst}".format(src=paths[0][1], dst=paths[0][-2])
        self.answer[EXP_KEY].append({
            'src':
            src,
            'dst':
            dst,
            'count':
            elephant_count,
            'msg_size':
            len(msg),
            'groundTruth':
            sw_src_dst,
            'paths': [','.join(p[1:-1]) + ',' for p in paths],
            'abnormalKind':
            'flow',
            'msg':
            msg
        })
        self.sleep(30)
        # self.sleep(30)
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
