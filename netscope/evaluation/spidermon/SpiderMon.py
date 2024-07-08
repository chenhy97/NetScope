import json
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict, namedtuple
from p4utils.utils.helper import load_topo

Degree = namedtuple("Degree", "name D in_w out_w")
if not os.path.abspath(__file__).endswith('netscope'):
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_path)
    from analysis.load import Loader


def load2df(df, topo):
    df['qdepths'] = df.debug.apply(lambda trace: [h['qdepth'] for h in trace])
    df['swid'] = df.debug.apply(lambda trace: [h['sw_id'] for h in trace])
    df['flow'] = df['src'] + '-' + df['dst']

    sw_data = []
    for pid, row in df.iterrows():
        for ih, hop in enumerate(row.debug):
            hop.update(dict(
                flow=row.flow,
                flow_t=row.timestamp,
                pid=pid,
            ))
            if ih < len(row.debug) - 1:
                leave_t = hop['timestamp'] + hop['deq_timedelta']
                hop.update(dict(
                    next_link_delay=row.debug[ih+1]['timestamp'] - leave_t))
            sw_data.append(hop)
    sw_dfs = pd.DataFrame(sw_data).sort_values('timestamp')
    sw_dfs['port'] = sw_dfs.apply(
        lambda r: f"s{r.sw_id},{topo.port_to_node(f's{r.sw_id}', r.eg_port)},", axis=1)
    return sw_dfs


class WFG():
    def __init__(self, sw_dfs, level='flow', MODE=1):
        G = nx.DiGraph()
        sw_dfs['vertex'] = sw_dfs[level]

        # Add nodes
        for v in sw_dfs.vertex.unique():
            G.add_node(v)

        # Add edges
        # for sw, sw_df in sw_dfs.groupby('sw_id'):  # 每个 switch
        # 每个 switch 上的 egress queue
        for (sw, eg_port), sw_df in sw_dfs.groupby(['sw_id', 'eg_port']):
            sw_df = sw_df.sort_values('timestamp', ignore_index=True)
            edges = defaultdict(lambda: defaultdict(int))
            # print(f"sw{sw}, eg {eg_port}")

            # 该 queue 上的每个数据包 (pkt sequence)
            for si, row in sw_df.iterrows():
                if row.qdepth == 0:
                    continue
                edge_from = row.vertex

                for d in range(1, 1+row.qdepth):
                    edge_to = sw_df.iloc[si-d].vertex
                    edges[edge_from][edge_to] += 1

            # # average
            # for vertex, vertex_df in sw_df.groupby('vertex'):
            #     if vertex not in edges:
            #         continue
            #     n = len(vertex_df)
            #     # print(n)
            #     for edge_to in edges[vertex].keys():
            #         edges[vertex][edge_to] /= n

            # add edge in G
            for edge_from in edges.keys():
                # print(edges[edge_from].keys())
                for edge_to, w in edges[edge_from].items():
                    edge = (edge_from, edge_to)
                    if edge in G.edges:
                        G[edge_from][edge_to]['weight'] += w
                    else:
                        # print(edge_from, edge_to)
                        G.add_edge(edge_from, edge_to, weight=w)
        self.G = G

    def find_contributors(self):
        G = self.G
        contributors = []
        for x in G.nodes:
            # any -> X: any wait for X
            in_w = sum([edge[2]['weight']
                        for edge in G.in_edges(x, data=True)])
            # X -> any: X wait for any
            out_w = sum([edge[2]['weight']
                         for edge in G.out_edges(x, data=True)])
            D = in_w - out_w
            # print(f"{x:<7}: {D:.2f}")
            # if D > 0:
            contributors.append(Degree(x, D, in_w, out_w))
        contributors = sorted(contributors, key=lambda c: c.D, reverse=True)
        return contributors
