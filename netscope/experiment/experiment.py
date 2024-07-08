#!/usr/bin/env python3
from collections import defaultdict
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI

import shutil
import os
from subprocess import Popen
import subprocess
import time
import json
from copy import deepcopy
import random
from pprint import pprint
import sys
import re
import requests
import json
import string
from pathlib import Path

from genpcaps import gen_pkts, wrpcap

DATASET_DIR_PATH = "/mnt/netscope/DataSet/univ1/"
DATA_SAVE_DIR_PATH = '/mnt/netscope/data'
CHAOSBLADE_EXCE_PATH = '/root/install/chaosblade-1.7.0/blade'

ROOT_PATH = Path(__file__).resolve().parent.parent

devNull = open(os.devnull, 'w')
with open(ROOT_PATH / 'build/config.txt', 'r') as f:
    INT_TYPE = f.read().strip('\n')
    print(INT_TYPE)

_user_pass = bytes("user@1\n", encoding="utf8")


class ExperimentBase():

    def __init__(self):
        # self.topo = load_topo("topology.json")
        self.topo = load_topo(ROOT_PATH / "build/topo_without_collector.json")
        self.hosts = self.topo.get_hosts()
        self.controller_fn = 'latency_controller'

        self.src_dir = ROOT_PATH / 'src/{INT_TYPE}'
        # self.popen_r = {}

        # self.answer = {exp_key: [] for exp_key in [
        #     'burst', 'port_queue', 'delay', 'drop', 'priority']}
        self.answer = defaultdict(list)

        self.send_list = []
        self.history = []
        self.killed = set()

        self.begin_t = time.strftime("%Y%m%d_%H%MGMT", time.localtime())
        self.root_folder = ROOT_PATH
        # self.root_folder = os.path.dirname(os.path.dirname((os.path.abspath(__file__))))

        # save random seed
        self.seed = random.randrange(sys.maxsize)
        self.history.append("random seed: %d" % self.seed)
        random.seed(self.seed)

        self.letters = string.ascii_letters + string.digits
        # get root permission
        os.popen('sudo -S echo "remember sudo~"', 'w').write('user@1\n')
        self.sleep(1)

    def ip2h(self, ip):
        return self.topo.ip_to_host[ip]['name']

    def refresh_log_folder(self):
        print("refresh log folder")
        self.host_log_folder = self.root_folder / 'log/hosts'
        for dir_name in ['send']:
            os.mkdir(self.host_log_folder / dir_name)

    def sleep(self, t):
        t_str = str(t) if isinstance(t, int) else f"{t:.2f}"
        log = 'sleep for %ss (%s GMT)' %\
            (t_str, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        print(log[:13])
        self.history.append(log)
        time.sleep(t)

    def digest(self):
        os.mkdir(self.host_log_folder / 'digest')
        for sw in self.topo.get_switches():
            cmd = [
                'sudo', 'python',
                str(self.src_dir / 'packet/digest.py'), sw
            ]
            log = open(self.host_log_folder / f'digest/{sw}.log', 'w')
            err_log = open(self.host_log_folder / 'digest/error.log', 'a+')
            Popen(cmd, stdout=log, stderr=err_log)
            print(" ".join(cmd))

    def replay_pcaps(self):
        if len(self.send_list) == 0:
            if os.path.exists("build/pcap"):
                print("Read pre-write pcap files.")
                for fn in os.listdir("build/pcap"):
                    self.send_list.append(tuple(fn.split('.')[0].split('-')))
            else:
                print("[W] No pcap files!")

        for (src, dst) in self.send_list:
            cmd = [
                "mx", src, "tcpreplay", f"--intf1={src}-eth0",
                "--preload-pcap", "--stats=1",
                os.path.join(self.root_folder, f'build/pcap/{src}-{dst}.pcap')
            ]
            # print(cmd)
            log = open(self.host_log_folder / f'send/{src}-{dst}.log', 'a+')
            p = Popen(cmd, stdout=log, stderr=log)

    def tcpreplay_edit(self,
                       src,
                       dst,
                       pt=None,
                       x=1,
                       loop=1,
                       stats=5,
                       limit=-1,
                       duration=-1,
                       pcap_path=None):
        """
        args ref: https://tcpreplay.appneta.com/wiki/tcpreplay-edit-man.html
        """
        dataset = Path(DATASET_DIR_PATH)
        PT = pt or 1
        pcap_path = pcap_path or (dataset / f'univ1_pt{PT}')
        # for (src, dst) in self.send_list:
        # sudo tcpreplay-edit -e 10.0.40.11:10.0.40.13 -K -q --cachefile cache/univ1_pt1_client.cache -I eth0 -i eth0 --enet-vlan=del univ1_pt1
        raw_cmd = [
            "mx",
            src,
            "tcpreplay-edit",
            # "-q", # "--quiet",
            "-K" if loop == 1 else "",  # "--preload-pcap",
            "--enet-vlan=del",
            # "--enet-dmac=ff:ff:ff:ff:ff:ff",
            f"--stats={stats}",
            f"--multiplier={x}",
            # "--pps=1",
            f"--intf1={src}-eth0",
            f"--intf2={src}-eth0",
            f"--loop={loop}" if loop > 1 else "",
            f"--limit={limit}" if limit > 0 else "",
            f"--duration={duration}" if duration > 0 else "",
            f"--cachefile={dataset / 'cache' / f'uv1_pt{PT}_client.cache'}",
            f"--endpoints={self.topo.get_host_ip(src)}:{self.topo.get_host_ip(dst)}",  #TODO: convert to ip
            str(pcap_path),
        ]
        cmd = [c for c in raw_cmd if not c.endswith("=None")]
        print(" ".join(cmd))
        self.history.append(" ".join(cmd))
        log = open(self.host_log_folder / f'send/{src}-{dst}_x{x}.log', 'a+')
        p = Popen(cmd, stdout=log, stderr=log)

    def check_pcap_finish(self):
        # print(os.listdir("/home/user/dds/netscope/log/hosts/send"))
        # for src, dst in self.send_list:
        #     print(f"check {src}")
        #     with open(os.path.join(self.host_log_folder, 'send', src+'.log'), 'rb') as f:
        #         f.seek(-200, 2)
        #         content = f.read().decode()
        #         if "Statistics for network device: " not in content:
        #             print("not finish")
        #             return False
        ps = Popen(f"ps -eaf | grep tcpreplay",
                   shell=True,
                   stdout=subprocess.PIPE)
        output = str(ps.stdout.read())[2:-1].replace('\\n', '\n')
        return output.count('\n') <= 2
        if output.count('\n') > 2:
            return False
        else:
            return True

    def send_pkt(self,
                 src,
                 dst,
                 msg="long_text_for_p4_test",
                 options=[],
                 append=True):
        options = [str(op) for op in options]
        src_path = f'./src/{INT_TYPE}/packet/send.py'
        log = open(self.host_log_folder / f'send/{src}.log', 'a+')
        err_log = open(self.host_log_folder / 'send/error.log', 'a+')
        cmd = [
            'sudo', 'mx', src, src_path,
            self.topo.get_host_ip(dst), '"' + msg + '"'
        ] + options
        p = Popen(cmd, stdout=log, stderr=err_log)
        if append:
            self.send_list.append((src, dst))
        self.history.append(" ".join(cmd))
        print(" ".join(cmd))
        print("send pkt from %s to %s (%s)" % (src, dst, " ".join(options)))
        print("\t", self.topo.get_shortest_paths_between_nodes(src, dst))
        return p

    def gen_random_host_pairs(self):
        for src in self.hosts:
            dst = random.choice([h for h in self.hosts if h != src])
            self.send_list.append((src, dst))

    def send(self, interval=1, priority=0, msg_size=(100, 200), options=[]):
        print('activate send.py for hosts')
        options_ = ['--interval',
                    str(interval), '--priority',
                    str(priority)] + options
        if len(self.send_list) == 0:
            print('random select sending src and dst')
            for src in self.hosts:
                self.sleep(random.random())
                dst = random.choice([h for h in self.hosts if h != src])
                msg = 'test-P4-' + ''.join([
                    random.choice(self.letters)
                    for _ in range(random.randint(*msg_size))
                ])
                self.send_pkt(src, dst, msg=msg, options=options_)
            print(self.send_list)
        else:
            print("preset send list")
            for src, dst in self.send_list:
                self.send_pkt(src,
                              dst,
                              msg='test-P4',
                              options=options_,
                              append=False)
                self.sleep(random.random())

    def controller(self, **kwargs):
        cmd = ['python', f'./src/{INT_TYPE}/{self.controller_fn}.py']
        for k, v in kwargs.items():
            cmd += [f'--{k}', str(int(v) if isinstance(v, float) else v)]
        log = open(self.host_log_folder / f'{self.controller_fn}.log', 'a+')
        p = Popen(cmd, stdout=log, stderr=log)
        print(" ".join(cmd))
        self.history.append(" ".join(cmd))
        return p

    def _kill_p(self, name, add=True):
        '''kill process'''
        if name in self.killed:
            return

        ps = Popen(f"ps -eaf | grep {name}",
                   shell=True,
                   stdout=subprocess.PIPE)
        output = str(ps.stdout.read())[2:-1].replace('\\n', '\n')
        if output.count('\n') > 2:
            print(f"killing {name}")
            # ps -ef | grep make | grep -v grep | cut -c 9-15 | xargs sudo kill -9
            Popen(
                f'ps aux | grep {name} | grep -v grep |  awk \'{{print $2}}\' | xargs sudo kill -9',
                shell=True)
            if add:
                self.killed.add(name)
        else:
            print(f"No {name} process was found.")

    def kill(self, names=None):
        '''kill all threads'''
        if names is None:
            names = [
                'send', 'receive', 'digest', self.controller_fn,
                'tcpreplay-edit', 'register_controller'
            ]

        if isinstance(names, list):
            for name in names:
                if name != "tcpreplay-edit":
                    p_name = name + '.py'
                else:
                    p_name = name + " "
                self._kill_p(p_name)
        elif isinstance(names, str):
            self._kill_p(names + '.py')
        else:
            raise TypeError(f"Should be list or str, but {type(names)} found.")

    def get_thrift_controllor(self, sw):
        thrift_port = self.topo.get_thrift_port(sw)
        controller = SimpleSwitchThriftAPI(thrift_port)
        return controller

    def set_queue_rate(self, p4switch, rate, egress_port=None):
        log = f"{p4switch}: set_queue_rate {rate} {egress_port}"
        print(log)
        self.history.append(log)
        ss_api = self.get_thrift_controllor(p4switch)
        ss_api.set_queue_rate(rate, egress_port)

    def init_all_queue_rate(self, rate):
        for sw in self.topo.get_p4switches():
            self.set_queue_rate(sw, rate)


class Experiment(ExperimentBase):

    def __init__(self):
        super().__init__()
        

    def run(self):
        '''begin experiment'''
        self.refresh_log_folder()
        quiet_time = 20
        interval = 0.4
        self.send(interval)
        # self.send_list = [('h1', 'h2')]
        
        self.sleep(quiet_time)
        self.send_pkt('h1',
                      'h2',
                      msg="this_is_victim_flow",
                      options=['--interval', str(0.01)])
        # self.send_pkt('h2', 'h5', msg="this_is_culprit_flow",
        #               options=['--interval', str(interval)])
        # self.sleep(60)  # basic prepare for ADR
        # self.sleep(30)
        # abnormal
        # self.send_pkt('h2', 'h5', msg="this_is_burst_flow",
        #               options=['--burst', '200'])
        # self.inject_abnormal()
        self.sleep(5)

        # end experiment
        # self.kill("send")
        # self.sleep(10)
        # self.kill("receive")
        self.kill("send")
        # print("\n======\nAnswer:")
        # print(self.get_iface_answer())

        self.finish()
        self.save_log("SZGD")

    def get_random_intf(self):
        while True:
            h_src, h_dst = random.choice(self.send_list)
            sw_path = random.choice(
                self.topo.get_shortest_paths_between_nodes(h_src, h_dst))[1:-1]
            if len(sw_path) > 1:
                sw_idx = random.randint(0, len(sw_path) - 2)
                port_num = self.topo.node_to_node_port_num(
                    sw_path[sw_idx], sw_path[sw_idx + 1])
                return "{}-eth{}".format(sw_path[sw_idx], port_num)

        # with open(os.path.join(self.host_log_folder, "interface.log"), "r") as f:
        #     interface = f.read()
        # interfaces = list(set(re.findall(r"s\d{1,2}-eth\d{1,2}", interface)))
        # while True:
        #     intf = random.choice(interfaces)
        #     port_from = intf.split('-')[0]
        #     port_to = self.topo.get_interfaces_to_node(port_from)[intf]
        #     if port_to[0] == 's':  # do not return link with host node
        #         return intf

    def inject_abnormal(self):
        print('\nbegin injection')
        self.sleep(10)

        intf = self.get_random_intf()
        self.chaos_group([
            # {'iface': 's1-eth2', 'timeout': 20, 'action': 'drop'},
            {
                'iface': intf,
                'timeout': 20,
                'time': 300,
                'offset': 200
            },
        ])
        self.sleep(15)

        intf = self.get_random_intf()
        self.chaos_group([
            {
                'iface': intf,
                'timeout': 30,
                'time': 200,
                'offset': 100
            },
            # {'iface': 's8-eth3', 'timeout': 20, 'time': 5000, 'offset': 2000},
        ])
        self.sleep(20)

    def chaos(self, iface, timeout, local_port=None, remote_port=None,  time=3000, offset=1000, action='delay'):
        print("inject %s" % action)
        blade = CHAOSBLADE_EXCE_PATH
        # blade = '/usr/lib/chaosblade/blade'
        Popen(f"sudo tc qdisc del dev {iface} root", shell=True)
        if action == 'delay':
            cmd = [
                'sudo', blade, 'create', 'network', action, '--time',
                str(time), '--offset',
                str(offset), '--interface', iface, '--timeout',
                str(timeout)
            ]
            if local_port is not None:
                cmd = cmd + ['--local-port', str(local_port)]
            if remote_port is not None:
                cmd = cmd + ['--remote-port', str(remote_port)]
            cmd = cmd + ["--force"]
            # sudo /home/user/install/chaosblade-1.7.0/blade create network delay --time 3000 --offset 500 --interface s1-eth2 --timeout 10
        elif action == "drop":
            cmd = [
                'sudo', blade, 'create', 'network', 'loss', '--percent', '100',
                '--interface', iface, '--timeout',
                str(timeout)
            ]
            # blade create network loss --percent 100 --interface s1-eth0 --timeout 20
        else:
            print("Unknown action")
            return

        print(' '.join(cmd))
        Popen(cmd)

        # if action not in self.answer:
        #     self.answer[action] = []

        # port_from = iface.split('-')[0]
        # port_to = self.topo.get_interfaces_to_node(port_from)[iface]
        # self.answer[action].append(
        #     {'iface': iface,
        #      'cmd': cmd,
        #      'groundTruth': '{},{},'.format(port_from, port_to),
        #      'abnormalKind': 'switch link'})
        print(action + " on " + iface)

    def chaos_group(self, group):
        timeout = max([c['timeout'] for c in group])
        for c in group:
            self.chaos(**c)
        print('\nfor chaos group,'),
        self.sleep(timeout)

    def get_iface_answer(self):
        '''check the interface is used in this experimnet'''
        with open(self.host_log_folder / 'sender.txt', 'w') as f:
            f.write('\n'.join([sr[0] for sr in self.send_list]))

        with open(self.host_log_folder / 'interface.log', 'r') as f:
            content = f.read()
        # answers = [a['iface'] for a in (
        #     self.answer.get('delay', []) + self.answer.get('drop', []) + self.answer.get('port_queue', []))]
        answers = [
            a['iface'] for a in (self.answer['delay'] + self.answer['drop'] +
                                 self.answer['port_queue'])
        ]
        answer = [a for a in answers if a in content]
        with open(self.host_log_folder / 'answer.txt', 'w') as f:
            f.write(', '.join(answer))
        return answer

    def wechat_bot(self, message):
        api = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=9a41bc20-dd0c-4a26-82d9-0f9d8c00a624'
        headers = {"Content-Type": "text/plain"}
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": message,
                "mentioned_list": ["@all"],
                "mentioned_mobile_list": ["@all"],
            }
        }
        r = requests.post(api, headers=headers, json=data)

    def save_log(self, kind):
        log_folder = Path(DATA_SAVE_DIR_PATH, INT_TYPE, kind, self.begin_t)

        print("data save at %s" % log_folder)
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        shutil.copytree(self.root_folder / 'log', log_folder / 'mininet')
        # print(os.listdir(self.root_folder / 'log'/'hosts'), '\n',
        #       os.listdir(log_folder / 'mininet' /'hosts'))
        # shutil.rmtree(os.path.join(log_folder, 'hosts/receive'))
        # shutil.rmtree(os.path.join(log_folder, 'hosts/send'))
        shutil.copyfile(self.root_folder / 'build/paths.json',
                        log_folder / 'paths.json')
        shutil.copyfile(self.root_folder / 'topology.json',
                        log_folder / 'topology.json')
        shutil.copyfile(self.root_folder / 'build/topo_without_collector.json',
                        log_folder / 'topo_without_collector.json')

        with open(log_folder / 'exp_history.txt', 'w') as f:
            f.write('\n'.join(self.history))
        with open(log_folder / 'answer.json', 'w') as f:
            json.dump(self.answer, f)
        with open(self.root_folder / 'build/build.json', 'w') as f:
            json.dump({'data_path': str(log_folder)}, f)
        os.popen(f"sudo -S chmod -R a+rwx /mnt/netscope/data",
                 'w').write('user@1\n')

    def copy_sw_log(self, log_dir='log/log', REG_L=8):
        os.mkdir(self.host_log_folder / 'log')
        for sw_fn in os.listdir(log_dir):
            with open(os.path.join(log_dir, sw_fn), 'r') as f:
                content = f.read()
                content = content.split('bm_reset_state')[-1]
            with open(self.host_log_folder / f'log/{sw_fn}', 'w') as f:
                f.write(content)

    def finish(self):
        self.kill()
        os.popen("sudo -S chmod -R a+rwx /mnt/netscope/data",
                 'w').write('user@1\n')
        with open(self.host_log_folder / 'answer.json', 'w') as f:
            json.dump(self.answer, f)
        # self.copy_sw_log()


if __name__ == '__main__':
    experiment = Experiment()
    experiment.run()
