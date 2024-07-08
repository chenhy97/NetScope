from experiment import Experiment
import random
import re
import time

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]


class Exp(Experiment):

    def run(self):
        '''begin experiment'''
        quiet_time = 20
        interval = 0.1

        self.refresh_log_folder()
        volumn = 20
        volumn = quiet_time / interval / 5
        self.controller(volumn=volumn, sigma_num=50, data_from='hosts')

        self.send(interval)
        # self.send_pkt('h1', 'h4', msg="this_is_victim_flow",
        #               options=['--interval', str(interval)])
        self.sleep(quiet_time)  # basic prepare for ADR

        # sleep(10)

        # # abnormal
        # # # abnormal
        while True:
            try:
                src, dst = random.choice(self.send_list)
                paths = self.topo.get_shortest_paths_between_nodes(src, dst)
                path = random.choice(paths)  # [1:-2]
                hop_id = random.randint(1, len(path) - 2 - 1)
                port = self.topo.node_to_node_port_num(path[hop_id],
                                                       path[hop_id + 1])
                rate = random.randint(3, 8)
                culprit_sw = path[hop_id]
                break
            except:
                continue
        intf = f"{culprit_sw}-eth{port}"

        timeout = random.randint(20, 30)  # seconds
        delay_time = random.randint(3000, 5000)
        offset = random.randint(100, min(delay_time, 1000))
        inject_t = int(time.monotonic() * 1e8)  # timestamp
        self.chaos_group([{
            'iface': intf,
            'timeout': timeout,
            'time': delay_time,
            'offset': offset
        }])
        self.answer[EXP_KEY].append(
            dict(src=src,
                 dst=dst,
                 paths=[','.join(p[1:-1]) + ',' for p in paths],
                 inject_t=inject_t,
                 intf=intf,
                 timeout=timeout,
                 groundTruth=path[hop_id] + "," + path[hop_id + 1] + ",",
                 abnormalKind='switch link'))
        self.sleep(10)

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
