import json
from pyecharts import options as opts
from pyecharts.charts import Graph
from pyecharts.render import make_snapshot
from snapshot_selenium import snapshot
from copy import deepcopy
import os
from pathlib import Path
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent

with open(ROOT_DIR / "topology.json", "r") as f:
    topo = json.load(f)

categories = [
    opts.GraphCategory(name="switch", symbol='circle'),
    opts.GraphCategory(name="host", symbol='rect'),
    opts.GraphCategory(name="culprit", symbol='circle'),
    # opts.GraphCategory(name="controller", symbol='rect'),
]


def node_category(node, culprits=None):
    culprits = culprits or []
    if node in ['h0', 's0']:
        category = 'controller'
    elif node.startswith('s'):
        if node in culprits:
            category = "culprit"
        else:
            category = 'switch'
    else:
        category = "host"
    return category


def gen_topo_png(png_fn, culprits=None):
    """by networkx"""
    remove_categories = ['controller']

    G = nx.Graph()

    for link in topo['links']:
        G.add_edge(link['node1'],
                   link['node2'],
                   port1=link['port1'],
                   port2=link['port2'])
    node_color = {
        'controller': '#b7524e',
        'switch': '#8aaed7',
        'host': '#488a85',
        'culprit': '#924747'
    }
    node_shape = {
        'controller': 'o',
        'switch': 'o',
        'host': 's',
        'culprit': 'o'
    }

    for node in [
            n for n in G.nodes() if node_category(n) in remove_categories
    ]:
        G.remove_node(node)

    # 根据不同的节点类别绘制图形
    pos = nx.spring_layout(G)
    plt.figure(figsize=(8, 8), dpi=100)
    for node in G.nodes():
        category = node_category(node, culprits)
        if category in remove_categories:
            continue
        nx.draw_networkx_nodes(G,
                               pos,
                               nodelist=[node],
                               node_color=node_color[category],
                               node_size=300,
                               node_shape=node_shape[category])

    nx.draw_networkx_edges(G, pos)
    nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
    plt.axis('off')
    plt.savefig(png_fn, bbox_inches='tight', pad_inches=0)
    plt.close()


def gen_topo_html(html_fn, culprits=None):
    """by pyecharts"""
    culprits = culprits or []

    nodes, links = [], []
    for node in topo['nodes']:
        name = node['id']
        # node
        if name in ['h0', 's0']:
            category = 'controller'
        elif name.startswith('s'):
            if name in culprits:
                category = "culprit"
            else:
                category = 'switch'
        else:
            category = "host"

        nodes.append(
            opts.GraphNode(name=name,
                           category=category,
                           value=node.get('ip', None),
                           symbol_size=25))

    for link in topo['links']:
        # add link
        link_conf = {
            'source': link['node1'],
            'target': link['node2'],
            'value': f"{link['port1']}/{link['port2']}",
            'symbol_size': 15,
        }
        links.append(opts.GraphLink(**link_conf))

    c = Graph(init_opts=opts.InitOpts(
        width="1000px", height="700px", bg_color="#ffffff"))
    c.add("",
          nodes,
          links,
          categories,
          repulsion=1000,
          edge_label=opts.LabelOpts(is_show=False,
                                    position="middle",
                                    formatter="{c}"),
          is_draggable=True)
    c.set_global_opts(title_opts=opts.TitleOpts(title="topology"))
    c.render(html_fn)


if __name__ == "__main__":
    rca = pd.read_csv(ROOT_DIR / "build/rca.csv")
    culprits = rca.iloc[0].culprit.strip(',').split(',')

    gen_topo_html(ROOT_DIR / "web/static/topo_origin.html")
    gen_topo_html(ROOT_DIR / "web/static/topo_culprit.html", culprits)

    gen_topo_png(ROOT_DIR / "web/static/topo_origin.png")
    # print(culprits)
    gen_topo_png(ROOT_DIR / "web/static/topo_culprit.png", culprits)
