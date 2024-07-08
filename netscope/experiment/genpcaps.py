#!/usr/bin/env python3
"""
IntSight Function
"""
import argparse
import sys
import socket
import random
import struct
import string
import math
import os

from scapy.all import sendp, send, get_if_list, get_if_hwaddr
from scapy.utils import wrpcap
from scapy.all import Packet
from scapy.all import Ether, IP, UDP, UDP
from scapy.all import Packet, IPOption
from scapy.all import PacketListField, ShortField, IntField, LongField, BitField, FieldListField, FieldLenField
from scapy.layers.inet import _IPOption_HDR

with open('build/config.txt', 'r') as f:
    INT_TYPE = f.read().strip('\n')
    print(INT_TYPE)
    sys.path.append(f"src/{INT_TYPE}/packet")
    from headers import IPOption_MRI

letters = string.ascii_letters + string.digits
lorem = ''.join(random.choice(letters) for _ in range(int(1e4)))  # 随机假文

root_folder = os.path.abspath(__file__)
for _ in range(4):
    root_folder = os.path.dirname(root_folder)
print(root_folder)


def Yred(x):
    return 15


def Yblue(x):
    return 15


def Yteal(x):
    return 15


def Ygreen(x):
    return 15


def Yorange(x):
    if x >= 30 and x <= 30.1:
        return 106.632
    return 15 * random.gauss(1, 0.1)


def gen_pkts(src_addr,
             dst_addr,
             yfunc,
             seconds,
             msg_len=500,
             hds_len=44,
             src_port=1234,
             dst_port=4321,
             lorem=lorem,
             add_noise=True):
    random.seed(42)
    x = 0
    i = 0
    pkts = []
    # iface = get_if()
    # print(iface, get_if_hwaddr(iface))

    while (x < seconds):
        # build packet
        beg = random.randint(0, 1e6 - msg_len - 1)
        pkt = (Ether(dst="ff:ff:ff:ff:ff:ff") /
               IP(src=src_addr,
                  dst=dst_addr,
                  options=IPOption_MRI(length=4, option=0)) /
               UDP(sport=src_port, dport=dst_port) / lorem[beg:beg + msg_len])
        pkt.time = x
        pkts.append(pkt)
        # calculate arrival time for next packet
        delay = 1.0 / ((yfunc(x) * 1e6) / (8 * (hds_len + msg_len)))
        if add_noise is True:
            noise = random.gauss(1, 0.1)
        else:
            noise = 1.0
        x = x + noise * delay
        # count pkts
        i = i + 1
        if i % 10000 == 0:
            print(i, end='...', flush=True)
        # elif i % 100 == 0:
        #     print(end='.', flush=True)
    print('done', flush=True)
    return pkts


def main():
    print('Building random string', end='...', flush=True)

    print('done', flush=True)

    seconds = 10.0
    maxframesize = 518 - 4  # Frame Check Sequence
    hdslen = 14 + 20 + 8  # Eth + IPv4 + UDP
    tellen = 33  # IntSight
    msglen = maxframesize - hdslen - tellen

    os.makedirs('resources/workloads/e2edelay', exist_ok=True)

    # print('Generating traffic for RED flow (h1-h10)')
    pkts = gen_pkts(src_addr='10.0.0.1',
                    dst_addr='10.0.0.8',
                    yfunc=Yred,
                    lorem=lorem,
                    seconds=seconds,
                    msg_len=msglen)
    print('Writting traffic to pcap file', end='...', flush=True)
    wrpcap('resources/workloads/e2edelay/h1-h8.pcp', pkts)
    print('done', flush=True)


if __name__ == '__main__':
    main()
