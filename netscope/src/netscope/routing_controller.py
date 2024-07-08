from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import argparse
import shutil
import os
import json
from pprint import pprint
from collections import defaultdict

import struct
import crcmod
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent.parent

crc16_func = crcmod.predefined.mkCrcFun('crc-16')

dir_default = "log/FIB"

SAMPLE_INTERVAL = str(int(1))
# SAMPLE_INTERVAL = str(int(1e6 / 5 * 2))
SAMPLE_INTERVAL = str(int(1e5))
# SAMPLE_INTERVAL = str(int(1e6))

QUEUE_RATE = 200


def hash_crc(path_id, sw_id, ingress_port, egress_port, control=0, divider=8):
    sw_id = int(str(sw_id).lstrip('s'))

    buffer = (path_id << 16) + sw_id
    buffer = (buffer << 9) + ingress_port
    buffer = (buffer << 9) + egress_port
    # buffer = (buffer << 3) + control
    buffer = (buffer << 3)

    new_path_id = crc16_func(struct.pack('>Q', buffer)) % divider
    new_path_id = (new_path_id + control) % divider
    return new_path_id


class Controller(object):

    def __init__(self, directory=dir_default, runtime=True, init=True):
        self.collector = 'h0'
        self.collector_sw = 's0'
        self.topo = load_topo(root_path / "topology.json")
        self.topo_no_s0 = load_topo(root_path /
                                    "build/topo_without_collector.json")
        self.controllers = {}

        self.directory = directory
        self.RUNTIME = runtime
        # print(self.directory, self.RUNTIME)

        if init:
            self.init()

    def init(self):

        def tree():
            return defaultdict(tree)

        self.entry_handles = tree()

        self.connect_to_switches()
        if self.RUNTIME:
            self.reset_states()

    def reset_states(self):
        [controller.reset_state() for controller in self.controllers.values()]

        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)  # remove dir
        os.mkdir(self.directory)  # make empty dir

    def connect_to_switches(self):
        for p4switch in self.topo.get_p4switches():
            thrift_port = self.topo.get_thrift_port(p4switch)
            if self.RUNTIME:
                self.controllers[p4switch] = SimpleSwitchThriftAPI(thrift_port)
            else:
                self.controllers[p4switch] = None

    def table_set_default(self, sw_name, table, action, args=[]):
        if self.RUNTIME:
            self.controllers[sw_name].table_set_default(table, action, args)
        self.write_files(
            sw_name,
            "table_set_default {} {} {}".format(table, action, " ".join(args)))

    def table_add(self, sw_name, table, action, key, args):
        content = "table_add {} {} {} => {}".format(
            table, action, " ".join([str(k) for k in key]),
            " ".join([str(a) for a in args]))
        if self.RUNTIME:
            entry_handle = self.controllers[sw_name].table_add(
                table, action, key, args)
            if entry_handle is not None:
                self.entry_handles[sw_name][table][action]['-'.join(
                    key)] = entry_handle
                self.write_files(sw_name, content)
        else:
            self.write_files(sw_name, content)

    def table_modify(self, sw_name, table_name, action_name, entry_handle,
                     action_params):
        content = "table_modify {} {} {} => {}".format(
            table_name, action_name, entry_handle,
            " ".join(map(str, action_params)))
        if self.RUNTIME:
            entry_handle_new = self.controllers[sw_name].table_modify(
                table_name, action_name, entry_handle, action_params)
            if entry_handle_new is not None:
                self.write_files(sw_name, content)
            return entry_handle_new
        else:
            self.write_files(sw_name, content)

    def mirroring_add(self, sw_name, session_id, port):
        if self.RUNTIME:
            self.controllers[sw_name].mirroring_add(session_id, port)
        self.write_files(sw_name,
                         "mirroring_add {} {}".format(session_id, port))

    def set_queue_rate(self, sw_name, rate):
        if self.RUNTIME:
            self.controllers[sw_name].set_queue_rate(rate)
        self.write_files(sw_name, "set_queue_rate {}".format(rate))

    def set_queue_depth(self, sw_name, queue_depth):
        if self.RUNTIME:
            self.controllers[sw_name].set_queue_depth(queue_depth)
        self.write_files(sw_name, "set_queue_depth {}".format(queue_depth))

    def write_files(self, sw_name, sw_string):
        with open(os.path.join(self.directory, sw_name + ".txt"), "a") as file:
            file.write(sw_string + "\n")


class RoutingController(Controller):

    def __init__(self, directory, runtime):
        super().__init__(directory, runtime)
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)  # delete dir
        os.makedirs(self.directory)  # make empty dir

        # print("runtime", self.RUNTIME)

    def main(self):
        print("hash path")
        self.hash_flows_path()
        print("add_INT_table")
        self.add_INT_tables()
        print("multicast")
        self.multicast()
        print("route")
        self.route()

        with open('build/entry_handle.json', 'w') as f:
            json.dump(self.entry_handles, f)
        os.popen("sudo -S chmod -R 777 build/*", 'w').write('user@1\n')
        os.popen(f"sudo -S chmod -R 777 {self.directory}/*",
                 'w').write('user@1\n')

    def add_INT_tables(self):
        for sw_name in self.controllers:
            if sw_name != self.collector_sw:
                self.set_queue_depth(sw_name, 8000)
                self.set_queue_rate(sw_name, QUEUE_RATE)
                self.mirroring_add(
                    sw_name, 2,
                    self.topo.node_to_node_port_num(sw_name,
                                                    self.collector_sw))
                self.table_add(sw_name, "get_sample_interval",
                               "set_sample_interval", [], [SAMPLE_INTERVAL])
                self.write_files(sw_name, "")

            self.table_add(sw_name, "get_port_num", "set_port_num", [],
                           [hex(len(self.topo.get_neighbors(sw_name)))])
            self.table_add(sw_name, "get_swid", "set_swid", [], [sw_name[1:]])
            self.table_add(sw_name, "get_swid_ingress", "set_swid_ingress", [],
                           [sw_name[1:]])
            # self.table_add(sw_name, "collector_header", "send_collector",
            #                [], [self.topo.get_host_ip(self.collector), self.topo.get_host_mac(self.collector_sw)])
            # self.table_add(sw_name, "collector_header", "send_collector",
            #                [], [self.topo.get_host_ip('h0'), self.topo.get_host_mac('s0')])
            # self.table_add(sw_name, "process_int_report", "report_header_init",
            #                [], [self.topo.get_host_ip(self.collector), self.topo.get_host_mac(self.collector_sw)])
            self.table_add(sw_name, "get_collector_ip", "set_collector_ip", [],
                           [self.topo.get_host_ip(self.collector)])

            for host in self.topo.get_hosts_connected_to(sw_name):
                host_ip = self.topo.get_host_ip(host)
                self.table_add(sw_name, "tb_int_source", "int_source",
                               [host_ip], [])
                self.table_add(sw_name, "tb_set_source", "int_set_source",
                               [host_ip], [])
                self.table_add(sw_name, "tb_set_sink", "int_set_sink",
                               [host_ip], [])

            for sw_dst in self.topo.get_p4switches():  # switch to switch
                if sw_dst == sw_name:
                    continue
                if not self.topo.get_hosts_connected_to(sw_dst):
                    continue
                for host in self.topo.get_hosts_connected_to(sw_dst):
                    host_ip = self.topo.get_host_ip(host) + "/32"
                    self.table_add(sw_name, "get_dst_swid", "set_dst_swid",
                                   [host_ip], [sw_dst[1:]])
                    self.table_add(sw_name, "get_src_swid", "set_src_swid",
                                   [host_ip], [sw_dst[1:]])

    def hash_flows_path(self):
        base = 2**3
        base_func_dict = {8: oct, 16: hex}
        path_json = {}
        for sw_src in self.topo_no_s0.get_p4switches():
            if 0 == len(self.topo_no_s0.get_hosts_connected_to(sw_src)):
                continue  # cannot be source switch
            for sw_dst in self.topo_no_s0.get_p4switches():
                if 0 == len(self.topo_no_s0.get_hosts_connected_to(sw_dst)):
                    continue  # cannot be destination switch

                if sw_dst == sw_src:
                    paths = [(sw_src, )]
                else:
                    paths = self.topo_no_s0.get_shortest_paths_between_nodes(
                        sw_src, sw_dst)

                # TODO: Confirm all path id satisfy all controls
                for path in paths:
                    control_dec = 0
                    while True:
                        controls = [
                            int(d, base) for d in base_func_dict[base](
                                control_dec)[2:].zfill(len(path))
                        ][::-1]

                        path_id = 0
                        path_id_history = [0]
                        egress_port_list, ingress_port_list = [], []

                        for i in range(len(path)):
                            # ingress port
                            if i == 0:
                                ingress_port = 0
                            else:
                                ingress_port = self.topo.node_to_node_port_num(
                                    path[i], path[i - 1])

                            # egress port
                            if i == len(path) - 1:
                                egress_port = 0
                            else:
                                egress_port = self.topo.node_to_node_port_num(
                                    path[i], path[i + 1])

                            ingress_port_list.append(ingress_port)
                            egress_port_list.append(egress_port)

                            # path id
                            path_id = hash_crc(path_id,
                                               path[i],
                                               ingress_port,
                                               egress_port,
                                               control=controls[i],
                                               divider=base)
                            path_id_history.append(path_id)

                        # save data
                        global_path_id = "{}-{}:{}".format(
                            sw_src, sw_dst, path_id)
                        # if global_path_id not in path_json:
                        #     path_json[global_path_id] = {}
                        # print("try ctrl", global_path_id, controls)

                        if global_path_id in path_json:
                            # print(global_path_id, controls)
                            if control_dec >= base**len(path) - 1:
                                print("fail to allocate control!")
                                print(path_id, path[i], ingress_port,
                                      egress_port, i)
                                print("control_dec", control_dec)
                                raise KeyError
                            control_dec += 1
                            continue

                        path_str = ','.join(path) + ','
                        path_json[global_path_id] = dict(
                            ingress_port_list=ingress_port_list,
                            egress_port_list=egress_port_list,
                            controls=controls,
                            path=path,
                        )

                        for i in range(len(path)):
                            if controls[i] == 0:
                                continue
                            self.table_add(path[i], "get_path_hash_control",
                                           "set_path_hash_control", [
                                               path[0][1:], path[-1][1:],
                                               str(egress_port_list[i]),
                                               str(path_id_history[i])
                                           ], [hex(controls[i])])
                            print("{} (path id: {}) control: {}".format(
                                path_str, path_id, controls))

                        # if len(path_json[sw_src_dst][path_id]) > 1:
                        #     print("{} {} conflict!".format(
                        #         sw_src_dst, path_id))
                        #     pprint(path_json[sw_src_dst][path_id])
                        break

        self.path_json = path_json
        return path_json

    def route(self):
        switch_ecmp_groups = {
            sw_name: {}
            for sw_name in self.topo.get_p4switches().keys()
        }

        for sw_name in self.controllers:
            # table default
            self.table_set_default(sw_name, "ecmp_group_to_nhop", "drop", [])
            self.table_set_default(sw_name, "ipv4_lpm", "drop", [])

            for sw_dst in self.topo.get_p4switches():  # switch to switch
                if sw_dst == sw_name:  # connect switch to neighbour host
                    for host in self.topo.get_hosts_connected_to(sw_name):
                        host_ip = self.topo.get_host_ip(host) + "/32"
                        host_mac = self.topo.get_host_mac(host)
                        host_port = self.topo.node_to_node_port_num(
                            sw_name, host)
                        self.table_add(
                            sw_name, "ipv4_lpm", "set_nhop", [str(host_ip)],
                            [str(host_mac), str(host_port)])
                    # print("table add at switch: {} | to host".format(sw_name))

                else:  # connect to other hosts (switchs)
                    if not self.topo.get_hosts_connected_to(sw_dst):
                        continue

                    if self.collector_sw in (sw_name, sw_dst):
                        backup_paths = self.topo.get_shortest_paths_between_nodes(
                            sw_name, sw_dst)
                    else:
                        # other paths should not go through s0
                        backup_paths = self.topo_no_s0.get_shortest_paths_between_nodes(
                            sw_name, sw_dst)

                    for host in self.topo.get_hosts_connected_to(sw_dst):
                        if len(backup_paths) == 1:
                            host_ip = self.topo.get_host_ip(host) + "/32"
                            next_hop_mac = self.topo.node_to_node_mac(
                                backup_paths[0][1], sw_name)
                            next_hop_port = self.topo.node_to_node_port_num(
                                sw_name, backup_paths[0][1])
                            self.table_add(
                                sw_name, "ipv4_lpm", "set_nhop",
                                [str(host_ip)],
                                [str(next_hop_mac),
                                 str(next_hop_port)])

                        elif len(backup_paths) > 1:
                            next_hops = [path[1] for path in backup_paths]
                            # for path in backup_paths:
                            #     next_hops.append(path[1])
                            next_hops_mac_port = []
                            for next_hop in next_hops:
                                next_hop_mac = self.topo.node_to_node_mac(
                                    next_hop, sw_name)
                                next_hop_port = self.topo.node_to_node_port_num(
                                    sw_name, next_hop)
                                # In order to be the key of dict
                                next_hops_mac_port.append(
                                    (next_hop_mac, next_hop_port))
                            # remove duplicate
                            next_hops_mac_port = list(set(next_hops_mac_port))
                            host_ip = self.topo.get_host_ip(host) + "/32"

                            if switch_ecmp_groups[sw_name].get(
                                    tuple(next_hops_mac_port), False):
                                ecmp_group_id = switch_ecmp_groups[
                                    sw_name].get(tuple(next_hops_mac_port))
                                self.table_add(sw_name, "ipv4_lpm",
                                               "ecmp_group", [str(host_ip)], [
                                                   str(ecmp_group_id),
                                                   str(len(next_hops_mac_port))
                                               ])
                            else:
                                ecmp_group_id = len(
                                    switch_ecmp_groups[sw_name]) + 1
                                switch_ecmp_groups[sw_name][tuple(
                                    next_hops_mac_port)] = ecmp_group_id

                                for i in range(len(next_hops_mac_port)):
                                    next_hop_mac = next_hops_mac_port[i][0]
                                    next_hop_port = next_hops_mac_port[i][1]

                                    self.table_add(
                                        sw_name, "ecmp_group_to_nhop",
                                        "set_nhop",
                                        [str(ecmp_group_id),
                                         str(i)], [
                                             str(next_hop_mac),
                                             str(next_hop_port)
                                         ])

                                self.table_add(sw_name, "ipv4_lpm",
                                               "ecmp_group", [str(host_ip)], [
                                                   str(ecmp_group_id),
                                                   str(len(next_hops_mac_port))
                                               ])

    def multicast(self):
        # ref: https://github.com/nsg-ethz/p4-learning/wiki/BMv2-Simple-Switch#creating-multicast-groups
        mc_group_id = 1
        rid = 0
        for sw_name in self.controllers:
            if sw_name == self.collector_sw:
                continue
            data = self.topo_no_s0.edge_to_intf[sw_name]
            ports = [
                data[s]['port'] for s in data
                if s.startswith('s') and s != self.collector_sw
            ]
            if self.RUNTIME:
                self.controllers[sw_name].mc_mgrp_create(mc_group_id)
                handle = self.controllers[sw_name].mc_node_create(rid, ports)
                self.controllers[sw_name].mc_node_associate(
                    mc_group_id, handle)

            self.write_files(
                sw_name,
                "mc_mgrp_create {ID}\nmc_node_create {rid} {ports}\nmc_node_associate {ID} {rid}"
                .format(ID=mc_group_id,
                        rid=rid,
                        ports=' '.join(map(str, sorted(ports)))))


def topo_remove_collector(s0='s0', h0='h0'):  # TODO: bug
    '''gen a clean topo without collector switch and host'''
    with open('topology.json', 'r') as f:
        topo = json.load(f)

    # remove node
    nodes = []
    for node in topo['nodes']:
        if node['id'] not in [s0, h0]:
            nodes.append(node)
    topo['nodes'] = nodes

    # remove link
    keys = ['source', 'target', 'node1', 'node2']
    links = []
    for link in topo['links']:
        if s0 not in [link[k] for k in keys]:
            links.append(link)
    topo['links'] = links

    with open('build/topo_without_collector.json', 'w') as f:
        json.dump(topo, f)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, required=False, default=dir_default)
    parser.add_argument("--runtime", action='store_true')
    parser.add_argument("--no-runtime", dest='runtime', action='store_false')
    parser.set_defaults(runtime=True)

    args = parser.parse_args()

    topo_remove_collector()

    controller = RoutingController(args.dir, args.runtime)
    controller.main()

    with open('build/paths.json', 'w') as f:
        json.dump(controller.path_json, f)
