# from p4utils.utils.helper import load_topo

# topo = load_topo('topology.json')


def host2sw(topo, h):
    '''host to direct switch'''
    return [neighbor for neighbor in topo.get_neighbors(h)
            if neighbor.startswith('s')][0]


def ip2h(topo, ip):
    return topo.ip_to_host[ip]['name']

# class Topo():
#     topo = load_topo('topology.json')

#     @classmethod
#     def host2sw(cls, h):
#         '''host to direct switch'''
#         return [neighbor for neighbor in cls.topo.get_neighbors(h)
#                 if neighbor.startswith('s')][0]

#     @classmethod
#     def ip2h(cls, ip):
#         return cls.topo.ip_to_host[ip]['name']
