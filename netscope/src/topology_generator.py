import json
import argparse
import networkx

parser = argparse.ArgumentParser()
parser.add_argument('--output_name',
                    type=str,
                    required=False,
                    default="p4app_test.json")
parser.add_argument('--p4_path',
                    type=str,
                    required=False,
                    default="p4src/ecmp.p4")
parser.add_argument("--topo", type=str, default="linear")
parser.add_argument("--bw", type=float, default=-1)
parser.add_argument('-n', type=str, required=False, default=2)
parser.add_argument('-d', type=str, required=False, default=4)
parser.add_argument('-k', type=str, required=False, default=4)
parser.add_argument('-l', type=str, required=False, default=4)
parser.add_argument('-s', type=str, required=False, default=4)
args = parser.parse_args()

topo_base = {
    "cli": True,
    # "pcap_dump": True,
    # "enable_log": True,
    "log_dir": "log/log",
    # "auto_arp_tables": False,
    "topology": {
        "assignment_strategy": "l2"
    }
}

SW_CONF = {
    # "cli_input": "./build/percentile_rules.txt"
    # "enable_debugger": True,
}


def link(src, dst, bw=args.bw, tags='ss'):
    cmd = [tags[0] + str(src), tags[1] + str(dst), {}]
    if bw != -1 and tags == 'ss':
        cmd[2]['bw'] = bw
    # cmd[2]['delay'] = 1000
    return cmd


def create_linear_topo(num_switches):
    topo_base["topology"]["links"] = []

    # connect hosts with switches
    for i in range(1, num_switches + 1):
        topo_base["topology"]["links"].append(
            ["h{}".format(i), "s{0}".format(i)])

    # connect switches
    for i in range(1, num_switches):
        topo_base["topology"]["links"].append(link(i, i + 1, args.bw))

    topo_base["topology"]["hosts"] = {
        "h{0}".format(i): {}
        for i in range(1, num_switches + 1)
    }
    topo_base["topology"]["switches"] = {
        "s{0}".format(i): SW_CONF
        for i in range(1, num_switches + 1)
    }


def create_fat_tree_topo(pods):
    topo_base["topology"]["links"] = []

    num_hosts = int((pods**3) / 4)
    num_agg_switches = pods * pods
    num_core_switches = int((pods * pods) / 4)

    hosts = [str(i) for i in range(1, num_hosts + 1)]

    core_switches = [str(i) for i in range(1, num_core_switches + 1)]
    agg_switches = [
        str(i) for i in range(num_core_switches + 1, num_core_switches +
                              num_agg_switches + 1)
    ]

    topo_base["topology"]["hosts"] = {"h" + h: {} for h in hosts}
    topo_base["topology"]["switches"] = {
        "s" + sw: SW_CONF
        for sw in (core_switches + agg_switches)
    }

    host_offset = 0
    for pod in range(pods):
        core_offset = 0
        for sw in range(int(pods / 2)):
            switch = agg_switches[(pod * pods) + sw]
            # Connect aggregate sw to core switches
            for _ in range(int(pods / 2)):
                core_sw = core_switches[core_offset]
                topo_base["topology"]["links"].append(
                    link(switch, core_sw, args.bw))
                core_offset += 1

            # Connect aggregate sw to edge sw in same pod
            for port in range(int(pods / 2), pods):
                edge_sw = agg_switches[(pod * pods) + port]
                topo_base["topology"]["links"].append(
                    link(switch, edge_sw, args.bw))

        for sw in range(int(pods / 2), pods):
            switch = agg_switches[(pod * pods) + sw]
            # Connect edge sw to hosts
            for _ in range(int(pods / 2), pods):
                host = hosts[host_offset]
                # All hosts connect on port 0
                topo_base["topology"]["links"].append(
                    link(switch, host, args.bw, tags='sh'))
                host_offset += 1


def create_circular_topo(num_switches):

    create_linear_topo(num_switches)
    # add link between  s1 and sN
    topo_base["topology"]["links"].append(link(1, num_switches, args.bw))


def create_random_topo(degree=4, num_switches=10):
    topo_base["topology"]["links"] = []
    g = networkx.random_regular_graph(degree, num_switches)
    trials = 0
    while not networkx.is_connected(g):
        g = networkx.random_regular_graph(degree, num_switches)
        trials += 1
        if trials >= 10:
            print("Could not Create a connected graph")
            return

    # connect hosts with switches
    for i in range(1, num_switches + 1):
        topo_base["topology"]["links"].append(
            ["h{}".format(i), "s{0}".format(i)])

    for edge in g.edges:
        topo_base["topology"]["links"].append(
            link(edge[0] + 1, edge[1] + 1, args.bw))

    topo_base["topology"]["hosts"] = {
        "h{0}".format(i): {}
        for i in range(1, num_switches + 1)
    }
    topo_base["topology"]["switches"] = {
        "s{0}".format(i): SW_CONF
        for i in range(1, num_switches + 1)
    }


def create_spine_leaf_topo(spine_n, leaf_n, h=2):
    topo_base["topology"]["hosts"] = {f"h{i+1}": {} for i in range(h * leaf_n)}
    topo_base["topology"]["switches"] = {
        f"s{i+1}": SW_CONF
        for i in range(spine_n + leaf_n)
    }
    topo_base["topology"]["links"] = []

    for leaf in range(spine_n + 1, spine_n + leaf_n + 1):
        for spine in range(1, spine_n + 1):
            topo_base["topology"]["links"].append(link(spine, leaf, args.bw))
        for i in range(h):
            topo_base["topology"]["links"].append(
                link(h * (leaf - spine_n - 1) + i + 1,
                     leaf,
                     args.bw,
                     tags='hs'))


def create_szgd_topo():
    """数字广东试验网络拓扑"""

    topo_base["topology"]["switches"] = {f"s{i+1}": SW_CONF for i in range(17)}

    topo_base["topology"]["links"] = []
    links = [link(1, 2), link(1, 6), link(2, 6), link(3, 4), link(3, 6)]
    links += [link(4, 6), link(5, 6), link(6, 11), link(6, 13), link(6, 7)]
    links += [link(6, 8), link(6, 17), link(11, 12), link(11, 9), link(7, 9)]
    links += [link(12, 10), link(8, 10), link(9, 10), link(11, 13)]
    links += [link(12, 14), link(13, 14), link(13, 15)]
    links += [link(14, 16), link(15, 16), link(16, 17)]
    host_i = 1
    links.append(link(host_i, 1, tags="hs"))
    host_i += 1
    links.append(link(host_i, 5, tags="hs"))
    host_i += 1
    links.append(link(host_i, 8, tags="hs"))
    host_i += 1
    links.append(link(host_i, 17, tags="hs"))

    topo_base["topology"]["hosts"] = {f"h{i+1}": {} for i in range(host_i)}

    topo_base["topology"]["links"] = links


if __name__ == '__main__':

    if args.topo == "linear":
        create_linear_topo(int(args.n))
    elif args.topo == "circular":
        create_circular_topo(int(args.n))
    elif args.topo == "random":
        create_random_topo(int(args.d), int(args.n))
    elif args.topo == "fat_tree":
        create_fat_tree_topo(int(args.k))
    elif args.topo == "spine_leaf":
        create_spine_leaf_topo(int(args.s), int(args.l))
    elif args.topo == 'szgd':
        create_szgd_topo()

    topo_base["p4_src"] = args.p4_path
    with open(args.output_name, "w") as f:
        json.dump(topo_base, f, sort_keys=True, indent=2)
