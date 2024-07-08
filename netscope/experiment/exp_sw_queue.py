import re
import random
from experiment import Experiment

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]


class Exp(Experiment):

    def __init__(self):
        Experiment.__init__(self)

    def run(self):
        '''begin experiment'''
        quiet_time = 20
        interval = 0.2

        self.refresh_log_folder()
        # self.controller(volumn=20, data_from='hosts')
        self.controller(volumn=quiet_time / interval / 5, data_from='hosts')
        self.send(interval)
        # self.send_pkt('h1', 'h4', msg="this_is_victim_flow",
        #               options=['--interval', str(interval)])
        # self.send_pkt('h3', 'h7', msg="this_is_victim_flow",
        #               options=['--interval', str(interval)])
        # self.send_pkt('h3', 'h1', msg="this_is_victim_flow",
        #               options=['--interval', str(interval)])
        self.sleep(quiet_time)  # basic prepare for ADR
        self.sleep(20)  # basic prepare for ADR

        src, dst = random.choice(self.send_list)
        paths = self.topo.get_shortest_paths_between_nodes(src, dst)
        path = random.choice(paths)  # [1:-2]
        hop_id = random.randint(1, len(path) - 2 - 1)
        port = self.topo.node_to_node_port_num(path[hop_id], path[hop_id + 1])
        rate = random.randint(5, 10)

        culprit_sw = path[hop_id]
        self.answer[EXP_KEY].append({
            'src':
            src,
            'dst':
            dst,
            'rate':
            rate,
            'port':
            port,
            'groundTruth':
            path[hop_id] + ',' + path[hop_id + 1] + ',',
            'paths': [','.join(p[1:-1]) + ',' for p in paths],
            'abnormalKind':
            'flow'
        })

        # # # abnormal
        self.set_queue_rate(culprit_sw, rate=rate, egress_port=port)
        self.sleep(10)
        self.set_queue_rate(culprit_sw, rate=100, egress_port=port)
        self.sleep(20)

        # # end experiment
        self.kill("send")
        self.sleep(1)  # wait for pkts forwarding in network
        self.finish()
        self.save_log(EXP_KEY)
        self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
