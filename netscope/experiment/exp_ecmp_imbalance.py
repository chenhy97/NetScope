from subprocess import Popen
import random
import os
import re
import shutil

from experiment import Experiment

EXP_KEY = re.findall(r'exp_(\w+?)\.py', __file__)[0]


class Exp(Experiment):

    def get_fork(self):
        try_list = []
        print(f"will try in {len(self.send_list)} times")
        while True:
            src, dst = random.choice(self.send_list)
            try_list.append((src, dst))
            print(src, dst)
            paths = self.topo.get_shortest_paths_between_nodes(src, dst)
            print(paths)
            if len(paths) > 1:
                fork = -1
                for i in range(len(paths[0])):
                    hops = [p[i] for p in paths]
                    if len(set(hops)) > 1:
                        fork = i - 1
                        break
                if fork == -1:
                    # didn't have a fork node
                    print("no fork node")
                    continue
                return (src, dst), paths[0][fork]
            else:
                print(f"{src}->{dst}: {len(paths)} paths")
                if len(try_list) == len(self.send_list):
                    print("All try failed!")
                continue

    def set_queue_rate(self, p4switch, rate, egress_port=None):
        print(f"{p4switch}: set_queue_rate {rate} {egress_port}")
        ss_api = self.get_thrift_controllor(p4switch)
        ss_api.set_queue_rate(rate, egress_port)

    def ECMP_imbalance(self, w1=1, w2=2, flow=None):
        src, dst = random.choice(self.send_list) if flow is None else flow
        paths = self.topo.get_shortest_paths_between_nodes(src, dst)
        if len(paths) > 1:
            fork = -1
            for i in range(len(paths[0])):
                hops = [p[i] for p in paths]
                if len(set(hops)) > 1:
                    fork = i - 1
                    break
            fork_ctrl = self.get_thrift_controllor(paths[0][fork])
            # key = [self.topo.get_hosts()[dst]['ip'].split('/')[0]+"/32"]
            args = list(map(str, [w1, w2]))
            entry = fork_ctrl.table_add("get_ECMP_weight", "set_ECMP_weights",
                                        [], args)

            self.answer['ecmp_imbalance'].append({
                'src':
                src,
                'dst':
                dst,
                'groundTruth':
                paths[0][fork],
                'paths': [','.join(p[1:-1]) + ',' for p in paths],
                'abnormalKind':
                'ecmp imbalance'
            })
            return (src, dst), entry
        else:
            print("ECMP imbalance need two paths")
            return

    def run(self):
        '''begin experiment'''
        quiet_time = 40
        interval = 0.1

        self.refresh_log_folder()
        # self.controller(volumn=20, data_from='hosts')
        self.controller(volumn=quiet_time / interval / 5,
                        sigma_num=50,
                        data_from='hosts')

        self.sleep(1)
        self.send_list = [
            ('h1', 'h8'), ('h1', 'h7'), ('h3', 'h7'), ('h4', 'h8'),
            ('h5', 'h6')
            #                   ('h5', 'h4'), ('h6', 'h2'), ('h7', 'h2'), ('h8', 'h3')
        ]
        self.send(interval)

        ei_flow, ei_fork = self.get_fork()
        print("ECMP imbalance flow:", ei_flow, "fork sw:", ei_fork)
        # self.send_pkt('h6', 'h2', options=["--interval", str(interval)])

        rate = 10
        for sw in self.topo.get_switches():
            self.set_queue_rate(sw, rate)
        # self.set_queue_rate(ei_fork, rate, egress_port=None)
        # self.set_queue_rate("s1", rate, egress_port=None)
        # self.set_queue_rate("s2", rate, egress_port=None)

        # self.sleep(quiet_time*2)

        # self.sleep(quiet_time*2)  # basic prepare for ADR
        self.sleep(quiet_time)
        self.sleep(10)

        # ========================
        # # inject abnormal begin
        # ========================
        # w2 = random.randint(4, 10)
        w2 = 10
        flow, entry = self.ECMP_imbalance(w1=1, w2=w2, flow=ei_flow)
        self.sleep(10)
        fork_ctrl = self.get_thrift_controllor(ei_fork)
        fork_ctrl.table_modify("get_ECMP_weight", "set_ECMP_weights", entry,
                               ["1", "1"])
        dst_sw = 6
        # reset histroy counter
        fork_ctrl.register_write("MyIngress.ECMP_bit", dst_sw * 2 + 0, 0)
        fork_ctrl.register_write("MyIngress.ECMP_bit", dst_sw * 2 + 1, 0)
        # ========================
        # # inject abnormal end
        # ========================

        self.sleep(10)
        self.sleep(30)
        # self.sleep(60)
        # self.sleep(60)
        # self.sleep(60*2)

        # end experiment
        self.kill("send")
        self.sleep(1)  # wait for pkts forwarding in network

        self.finish()
        self.save_log(EXP_KEY)
        self.wechat_bot(f"Finish: {EXP_KEY}")


if __name__ == '__main__':
    exp = Exp()
    exp.run()
