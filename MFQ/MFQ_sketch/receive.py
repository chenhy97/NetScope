from scapy.all import sniff, sendp, hexdump, get_if_list, get_if_hwaddr
from headers import *
import sys, os
import argparse
import json
import ipdb
from pprint import pprint
import socket
import struct
import time

import netifaces

DEBUG = False
DEBUG = True

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('iface', help='interface', type=str, default='h2-eth0')
    parser.add_argument('--simple',
                        help='just load data',
                        type=bool,
                        required=False,
                        default=False)
    return parser.parse_args()
def get_header_size(hdr_t):
    return int(sum([field.size for field in hdr_t.fields_desc]) / 8)
class Receive():
    def __init__(self, iface):
        self.iface = iface
        self.count = 0
        self.latency_list = []
    def parse_header(self, hdr_t):
        offset = get_header_size(hdr_t)
        offset = int(offset)
        hdr = hdr_t(self.raw_load[:offset])
        self.headers.append(hdr)
        return hdr
    def handle_pkt(self, pkt):
        self.headers = []
        receive_t = int(time.monotonic() * 1e8)  # timestamp
        self.raw_load = bytes(pkt["TCP"])[20:]
        # print(len(self.raw_load))
        int_hdr = self.parse_header(INT_Header)
        # int_hdr.show()
        print()
        self.latency_list.append("'src_ip':'{}','sport':{},'dst_ip':'{}','dport':{},'latency':{}, 'lambda_value':{}, 'count':{}, 'c_minus':{}, 'c_plus':{}, 'max_gap':{}, 'min_gap':{}, 'quantile0':{}, 'max_value':{}, 'min_value':{}, ".format(\
                                     pkt["IP"].src, pkt["TCP"].sport,  pkt["IP"].dst,pkt["TCP"].dport, \
                                     int_hdr.latency, int_hdr.lambda_value0, \
                                     int_hdr.count_sketch,\
                                     int_hdr.c_minus_value_sketch0,int_hdr.c_plus_value_sketch0, \
                                     int_hdr.max_gap_value_sketch0,int_hdr.min_gap_value_sketch0,\
                                     int_hdr.quantile_value_sketch0, \
                                     int_hdr.max_value_sketch0, int_hdr.min_value_sketch0, ))
        # self.latency_list.append("'src_ip':'{}','sport':{},'dst_ip':'{}','dport':{},'latency':{}, 'lambda_value':{}, 'count':{}, 'count_0':{}, 'count_1':{}, 'count_2':{}, 'c_minus':{}, 'c_plus':{}, 'max_gap':{}, 'min_gap':{}, 'quantile0':{}, 'quantile1':{}, 'quantile2':{}, 'index0':{}, 'index1':{}, 'index2':{}, 'latency_bk':{}, 'lat_ts_value_sketch_bk':{},".format(\
        #                              pkt["IP"].src, pkt["TCP"].sport,  pkt["IP"].dst,pkt["TCP"].dport, \
        #                              int_hdr.latency, int_hdr.lambda_value0, \
        #                              int_hdr.count_sketch,int_hdr.count_sketch0,int_hdr.count_sketch1,int_hdr.count_sketch2, \
        #                              int_hdr.c_minus_value_sketch0,int_hdr.c_plus_value_sketch0, \
        #                              int_hdr.max_gap_value_sketch0,int_hdr.min_gap_value_sketch0,\
        #                              int_hdr.quantile_value_sketch0,int_hdr.quantile_value_sketch1, int_hdr.quantile_value_sketch2, \
        #                              int_hdr.prev_index_sketch0,int_hdr.prev_index_sketch1, int_hdr.prev_index_sketch2, \
        #                              int_hdr.temp_ingr_ts, int_hdr.temp_egr_ts))
        print(len(self.latency_list))
        # print(int_hdr.latency)
        # sys.stdout.flush()

def main(iface, saved_file_name):
    
    sys.stdout.flush()
    print("sniffing on %s"%iface)
    receive = Receive(iface)
    with open(saved_file_name,"w") as f:
        pass
    sniff(iface=iface, prn=lambda x:receive.handle_pkt(x))
    print(len(receive.latency_list))
    with open(saved_file_name,"w") as f:
        for item in receive.latency_list:
            f.write("{"+str(item)+"}\n")
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("--replay", help = "replay packets send", type=str, required=False, default = "True")
    parser.add_argument("--iface", help = "interface", type=str, required=True, default="h2-eth0")
    args = parser.parse_args()
    if args.replay == "True":
        saved_file_name = f"log/hosts/{args.iface}_new.json"
    else:
        saved_file_name = f"log/hosts/{args.iface}.json"
    # print(args.iface,saved_file_name)
    main(args.iface,saved_file_name)