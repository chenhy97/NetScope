from subprocess import Popen
import random
import os
import sys
import re
import shutil

if True:
    root_path = os.getcwd()
    sys.path.append(os.path.join(root_path, 'experiment'))
    from experiment import Experiment

EXP_KEY = re.findall(r'(\w+?)\.py', __file__)[0]

'''make test exp=evaluation/syndb/burst_sync.py exp_dir=eval'''


class Exp(Experiment):
    def run(self):
        '''begin experiment'''

        quiet_time = 15
        interval = 0.5

        self.refresh_log_folder()
        self.init_all_queue_rate(60)

        self.sleep(1)
        # self.send(interval)
        for i in range(6):
            self.send_pkt(f'h{i+1}', 'h8', msg="this_is_synchronized_flow",
                          options=['--interval', str(interval),
                                   '--times', str(5),
                                   '--random', str(0.2),
                                     #    '--times', '1'
                                   ]
                          )
        # self.sleep(quiet_time)  # basic prepare for ADR
        self.sleep(10)
        # self.sleep(quiet_time*2)
        # self.sleep(10)

        # # # inject abnormal
        # burst_src, burst_dst = random.choice(self.send_list)
        # # burst_min = 300
        # # burst_count = random.randint(burst_min, burst_min+100)
        # burst_count = 300

        # self.send_pkt(burst_src, burst_dst,
        #               msg="this_is_burst_flow"+''.join(
        #                   [random.choice(self.letters)
        #                    for i in range(random.randint(1000, 1200))]),
        #               options=['--burst', burst_count])

        # # save answer
        # paths = self.topo.get_shortest_paths_between_nodes(
        #     burst_src, burst_dst)
        # sw_src_dst = "{src}-{dst}".format(src=paths[0][1], dst=paths[0][-2])
        # self.answer['burst'].append({'src': burst_src, 'dst': burst_dst,
        #                              'count': burst_count,
        #                              'groundTruth': sw_src_dst,
        #                              'paths': [','.join(p[1:-1])+',' for p in paths],
        #                              'abnormalKind': 'flow'})
        # self.sleep(10)
        # self.sleep(30)
        # self.sleep(30)

        # end experiment
        self.kill("send")
        self.sleep(2)  # wait for pkts forwarding in network

        self.finish()
        # self.save_log(EXP_KEY)
        # self.save_log("burst")
        self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
