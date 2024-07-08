from email.mime import base
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import argparse
import shutil
import os
import json
import sys
import time

import numpy as np
import subprocess
from collections import defaultdict, namedtuple
from routing_controller import Controller

if True:
    sys.path.append(os.getcwd())
    from analysis.reservoir import Reservoir

FlowTh = namedtuple('FlowThreshold', 'sink threshold')

ZOOM = 1
MAX_LATENCY = np.inf

RESET_T = 15  # seconds


class CSV_logger():

    def __init__(self, fn):
        self.fn = fn
        with open(self.fn, 'a+') as f:
            f.write("flow,threshold,timestamp\n")

    def log(self, flow, threshold):
        with open(self.fn, 'a+') as f:
            f.write(f"{flow},{threshold},{int(time.monotonic()*1e8)}\n")


class LatencyController(Controller):

    def __init__(self,
                 volumn,
                 sigma_num,
                 interval,
                 sigma_num_short=None,
                 data_from='controller',
                 update_type='both'):
        """
        @update_type: {both, long, short}
        """
        super().__init__(init=False)
        self.log_dir = 'log/hosts'
        self.entry_handle_path = 'build/entry_handle.json'

        self.table = 'get_latency_threshold'
        self.action = 'set_latency_threshold'

        self.interval = interval
        self.sigma_num = sigma_num
        self.update_type = update_type

        self.init_t = time.time()
        self.volumn = int(volumn)

        self.data_from = data_from
        if data_from == 'controller':
            self.latency_fn = '-eth0-28.json'
            self.update = self.update_controller
            self.feed_reservoir = self.feed_reservoir_contoller
            self.last_read = 0
        else:
            self.latency_fn = '-eth0-31.json'
            self.update = self.update_hosts
            self.feed_reservoir = self.feed_reservoir_hosts
            self.last_read = defaultdict(int)

        self.reservoirs = dict(
            short=Reservoir(volumn=self.volumn * 5,
                            sigma_num=sigma_num_short or self.sigma_num))
        self.reservoirs_tag = defaultdict(lambda: False)

        print(f"V: {volumn}, sigma: {sigma_num}")
        self.thresholds = defaultdict(int)
        self.log = CSV_logger(os.path.join('log', 'LC.csv'))
        self.init()

    def ip2h(self, ip):
        return self.topo.ip_to_host[ip]['name']

    def init(self):
        self.connect_to_switches()

        def tree():
            return defaultdict(tree)

        self.entry_handles = tree()

        # update entry_handle with data in file
        with open(self.entry_handle_path, 'r') as f:
            self.entry_handles.update(json.load(f))
            for sw, data in self.entry_handles.items():
                self.entry_handles[sw] = defaultdict(tree, data)

        print("Begin Latency Controller")
        print(f"Reservoir volumn is {self.volumn}")

    def update_hosts(self):
        for h in self.topo.get_hosts():
            self.update_controller(h)

    def update_controller(self, h='h0'):
        fn = os.path.join(self.log_dir, h + self.latency_fn)
        if not os.path.exists(fn):
            # print(f"[W] File not exists yet: {fn}")
            return

        flows = {}
        with open(fn, 'rb') as f:
            # seek only valid in bytes mode
            f.seek(self.last_read[h], 1)
            counter = 0
            for line in f.readlines():
                counter += 1
                data = json.loads(str(line.decode()).strip(',\n'))
                flow, flow_th = self.update_reservoir(data)
                # print(flow_th, data)
                if flow_th is not None:
                    flows[flow] = flow_th
            self.last_read[h] = f.tell()
            print("flows to update:", flows.keys())
            print(
                f"Read {fn} with {counter} lines, now seeks at {self.last_read[h]}\n"
            )

        for flow, data in flows.items():
            self.update_sw_config(flow, data.sink,
                                  min(data.threshold, MAX_LATENCY))

        self.save_entry_handle()

    def feed_reservoir_hosts(self, data):
        dst_h_name = data['dst_ip']

        def name2ip(name):
            return self.topo.get_hosts()[name]['ip'].split('/')[0]

        flow = f"{name2ip(data['src_ip'])}-{name2ip(data['dst_ip'])}-{data['src_port']}-{data['dst_port']}-{data['protocol']}"

        if flow not in self.reservoirs:
            self.reservoirs[flow] = Reservoir(volumn=self.volumn,
                                              sigma_num=self.sigma_num)
        self.reservoirs[flow].feed(data['latency'])
        self.reservoirs["short"].feed(data['latency'])

        return flow, dst_h_name

    def feed_reservoir_contoller(self, data):
        shim = data['latency_shim']
        flow = f"{shim['src_ip']}-{shim['dst_ip']}-{shim['src_port']}-{shim['dst_port']}-{shim['protocol']}"
        dst_h_name = self.topo.ip_to_host[shim['dst_ip']]['name']
        if flow not in self.reservoirs:
            self.reservoirs[flow] = Reservoir(volumn=self.volumn,
                                              sigma_num=self.sigma_num)
        count = shim['count']  # may bug still
        for l in data['latency'][:count]:
            if l == 0:
                print("[N] Encounter 0")
                continue
            self.reservoirs[flow].feed(l)
            self.reservoirs["short"].feed(l)

        return flow, dst_h_name

    def update_reservoir(self, data):
        '''udpate by feed'''
        #: In time RESET_T period, the network is initializing. No data should be fed in reservoir
        if time.time() - self.init_t < RESET_T:
            return "ignored_flow", None

        flow, dst_h_name = self.feed_reservoir(data)

        flow_reservoir = self.reservoirs[flow]

        if len(flow_reservoir.R_sub) == 0:
            # print(f"flow ({flow}) need more data to feed")
            return flow, None
        else:
            threshold = np.median(flow_reservoir.R_sub) + \
                np.std(flow_reservoir.R_sub) * flow_reservoir.sigma_num
            # print("sigma", flow_reservoir.sigma_num)
            # threshold = flow_reservoir.threshold()
            # print(threshold, np.median(flow_reservoir.R))

            sink_sw = [
                neighbor for neighbor in self.topo.get_neighbors(dst_h_name)
                if neighbor.startswith('s')
            ][0]

            return flow, FlowTh(sink_sw, int(threshold / ZOOM))

    def update_mat(self, sw, table, action, key, threshold, log=True):
        threshold = str(threshold)
        key_str = "-".join(key)
        if key_str in self.entry_handles[sw][table][action]:
            print(f"[M] Modify threshold for flow {key_str} to {threshold}")
            self.table_modify(sw, table, action,
                              self.entry_handles[sw][table][action][key_str],
                              [threshold])
        else:
            print(f"[A] Set threshold {threshold} for flow {key_str}")
            self.table_add(sw, table, action, key, [threshold])

        if log:
            self.thresholds[key_str] = threshold
            self.log.log(key_str, threshold)

    def update_sw_config(self, flow, sw, threshold):
        '''switch config command'''
        if int(threshold) >= 2**48:
            # In case of "Parameter is too large"
            threshold = str(int(2**48 - 1))
        threshold = str(threshold)
        threshold_str = f"[{threshold:>6}]"
        flow_str = f"[{flow:<32}]"
        if self.thresholds[flow] == threshold:
            print(
                f"[S] Same threshold {threshold_str} for flow {flow_str}, pass."
            )
            return

        t = int(time.monotonic() * 1e8)  # timestamp

        print(self.reservoirs[flow].R_sub)
        self.thresholds[flow] = threshold

        if self.update_type in ['both', 'long']:
            if flow in self.entry_handles[sw][self.table][self.action]:
                print(
                    f"[M] [T:{t}] Modify threshold for flow {flow_str} to {threshold_str}"
                )
                self.table_modify(
                    sw, self.table, self.action,
                    self.entry_handles[sw][self.table][self.action][flow],
                    [threshold])
            else:
                print(
                    f"[A] [T:{t}] Set threshold {threshold_str} for flow {flow_str}"
                )
                self.table_add(sw, self.table, self.action, flow.split('-'),
                               [threshold])
            self.log.log(flow, threshold)
            self.update_threshold_host_level(flow, sw)

    def save_entry_handle(self):
        with open(self.entry_handle_path, 'w') as f:
            json.dump(self.entry_handles, f)

    def check_p4run_end(self):
        ps = subprocess.Popen("ps -eaf | grep p4run",
                              shell=True,
                              stdout=subprocess.PIPE)
        output = str(ps.stdout.read())[2:-1].replace('\\n', '\n')
        if output.count('\n') > 1:  # grep --color=auto p4run
            return False
        else:
            return True

    def update_threshold_host_level(self, flow, sw):
        host_pair = flow.split("-")[:2]
        host_key = "-".join(host_pair)

        host_pair_max_th = np.max(
            [int(v) for k, v in self.thresholds.items() if host_key in k])
        if self.thresholds[host_key] != str(host_pair_max_th):
            self.update_mat(sw, "get_latency_threshold_host", self.action,
                            host_pair, host_pair_max_th)

    def update_edge_sw_level(self):
        edge_sw_pairs = defaultdict(int)
        for flow, threshold in self.thresholds.items():
            # if "-" not in flow and "." not in flow:
            if flow.count("-") < 3:
                continue  # switch pair, not ip
            src_ip, dst_ip = flow.split("-")[:2]
            src_h, dst_h = self.ip2h(src_ip), self.ip2h(dst_ip)
            path = self.topo.get_shortest_paths_between_nodes(src_h, dst_h)[0]
            src_swid, dst_swid = path[1], path[-2]
            pair = (src_swid, dst_swid)
            # if pair not in edge_sw_pairs:
            #     edge_sw_pairs[pair] = threshold
            # else:
            edge_sw_pairs[pair] = max(edge_sw_pairs[pair], int(threshold))

        for pair, threshold in edge_sw_pairs.items():
            src_swid, dst_swid = pair
            self.update_mat(dst_swid,
                            "get_latency_threshold_edge_sw",
                            "set_latency_threshold",
                            [src_swid.lstrip("s"),
                             dst_swid.lstrip("s")],
                            str(threshold),
                            log=True)

    def update_short_flow(self):
        reservoir = self.reservoirs['short']
        if len(reservoir.R_sub) == 0:
            return
        threshold = np.median(
            reservoir.R_sub) + np.std(reservoir.R_sub) * reservoir.sigma_num
        print("stat", np.median(reservoir.R_sub), np.std(reservoir.R_sub),
              reservoir.sigma_num)
        threshold = int(threshold / ZOOM)

        if self.thresholds["short"] == threshold:
            print(f"[S] Same threshold {threshold} for short flows, pass.")
            return

        self.thresholds["short"] = threshold

        t = int(time.monotonic() * 1e8)  # timestamp

        threshold = str(threshold)
        threshold_str = f"[{threshold:>6}]"

        for sw in self.topo.get_switches():
            if sw == self.collector_sw: continue

            self.update_mat(sw,
                            "get_short_latency_threshold",
                            "set_latency_threshold", [],
                            threshold,
                            log=False)
        self.log.log("short", threshold)

    def run_loop(self):
        while True:
            sys.stdout.flush()
            # check mininet is die and break
            if self.check_p4run_end():
                print("p4run is dead. Controller down.")
                break
            time.sleep(self.interval)
            print("\n", "==" * 20, sep="")
            print("Update Epoch\n")
            self.update()
            if self.update_type in ['both', 'short']:
                self.update_edge_sw_level()
                self.update_short_flow()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--volumn", type=int, default=10)
    parser.add_argument("-s", "--sigma_num", type=int, default=3)
    parser.add_argument("-f", "--data_from", type=str, default='controller')
    parser.add_argument("-i", "--interval", type=float, default=2)
    parser.add_argument("-u", "--update_type", type=str, default='both')
    parser.add_argument("--sigma_num_short", type=int, default=3)

    args = parser.parse_args()

    LC = LatencyController(
        volumn=args.volumn,
        sigma_num=args.sigma_num,
        interval=args.interval,
        sigma_num_short=args.sigma_num_short,
        data_from=args.data_from,
        update_type=args.update_type,
    )
    LC.run_loop()
