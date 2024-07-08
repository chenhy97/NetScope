#!/usr/bin/env python3
import random
import os
import sys
import re
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

    def run(self):
        '''begin experiment'''
        quiet_time = 20
        interval = 0.2

        self.refresh_log_folder()
        # self.controller(volumn=50, data_from='hosts')
        # self.controller(volumn=100, sigma_num=3, data_from='hosts')
        self.controller(data_from='hosts',
                        update_type='short',
                        **config['controller'])

        self.sleep(1)
        self.send_list = []
        # self.send(interval)
        for src in self.hosts:
            dst = random.choice([h for h in self.hosts if h != src])
            self.send_list.append((src, dst))

        for src, dst in self.send_list:
            pt = random.randint(1, 20)
            self.tcpreplay_edit(src, dst, pt=pt, x=0.1)
        # self.tcpreplay_edit(src, dst, x=1, limit=1)
        # break
        print(self.send_list)

        self.sleep(config['time']['init'])

        self.sleep(10)
        self.sleep(30)

        # end experiment
        self.kill("send")

        self.finish()
        self.save_log(EXP_KEY)
        # self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
