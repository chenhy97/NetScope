#!/usr/bin/env python

import argparse
import sys
import socket
import random
import struct

from scapy.all import sendp, send, hexdump, get_if_list, get_if_hwaddr
from scapy.all import Ether, IP, UDP

from time import sleep
import time

from headers import IPOption_MRI


def get_if():
    iface = None  # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface = i
            break
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('dst', help='destination', type=str)
    parser.add_argument('msg', help='message', type=str)
    parser.add_argument('--times',
                        help='repeat times',
                        type=int,
                        required=False,
                        default=1)
    parser.add_argument('--interval',
                        help='interval time(s)',
                        type=float,
                        required=False,
                        default=0)
    parser.add_argument('--random',
                        help='random time gap',
                        type=float,
                        required=False,
                        default=0)
    parser.add_argument('--burst',
                        help='microburst in 1s',
                        type=int,
                        required=False,
                        default=0)
    parser.add_argument('--max_count',
                        help='stop when reach max count',
                        type=int,
                        required=False,
                        default=0)
    parser.add_argument('--priority',
                        help='packet priority',
                        type=int,
                        required=False,
                        default=0)
    return parser.parse_args()


def main():
    args = get_args()
    print(args.msg)

    addr = socket.gethostbyname(args.dst)
    iface = get_if()

    tos = int(bin(args.priority)[2:].zfill(3) + '00000', 2)

    print(iface, get_if_hwaddr(iface))

    pkt = (
        Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff") /
        # IP(dst=addr, options=IPOption_MRI(length=4, option=0), tos=tos) /
        IP(dst=addr, tos=tos) / UDP(dport=4321, sport=1234) / args.msg)

    pkt.show2()
    sys.stdout.flush()
    # hexdump(pkt)

    # first consider infinitly send, or send limited times
    if args.interval:
        count = 0
        while True:
            for _ in range(args.times):
                count += 1
                sendp(pkt, iface=iface)
            sleep(args.interval)
            sleep(random.random() * args.random)
            if args.max_count > 0 and count >= args.max_count:
                break
    elif args.burst:
        burst_map = map(lambda x: sendp(pkt, iface=x),
                        [iface] * int(args.burst))
        # burst_map = [sendp(pkt, iface=iface) for _ in range(int(args.burst))]
        # print(len(burst_map))
        print("burst count:", len(list(burst_map)))
        # for _ in range(int(args.burst)):
        #     sendp(pkt, iface=iface)
    else:
        try:
            for i in range(int(args.times)):
                sendp(pkt, iface=iface)
                sleep(1)
                sleep(random.random() * args.random)
        except KeyboardInterrupt:
            raise


if __name__ == '__main__':
    main()
