import json
import sys

isPY2 = sys.version_info.major == 2

if isPY2:
    sys.path.append("/home/ben/.local/lib/python2.7/site-packages")
    from graph_p4utils import NetworkGraph as NetworkGraph_p4utils
else:
    from .graph_p4utils import NetworkGraph as NetworkGraph_p4utils

from networkx.readwrite.json_graph import node_link_graph


def load_topo(json_path):
    """Load the topology from the path provided.

    Args:
        json_path (string): path of the JSON file to load

    Returns:
        p4utils.utils.topology.NetworkGraph: the topology graph.
    """
    with open(json_path, 'r') as f:
        graph_dict = json.load(f)
        graph = node_link_graph(graph_dict)
    return NetworkGraph(graph)


class NetworkGraph(NetworkGraph_p4utils):

    def __init__(self, *args, **kwargs):
        super(NetworkGraph, self).__init__(*args, **kwargs)

    def get_all_hosts_ip(self):
        return [v['ip'] for host, v in self.get_hosts().items()]

    if isPY2:

        def get_hosts(self):
            return {n: self.nodes[n] for n in self.nodes if self.isHost(n)}

        def get_switches(self):
            return {n: self.nodes[n] for n in self.nodes if self.isSwitch(n)}

        def get_p4switches(self):
            return {n: self.nodes[n] for n in self.nodes if self.isP4Switch(n)}
