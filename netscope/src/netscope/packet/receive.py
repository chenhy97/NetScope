#!/usr/bin/env python3
from scapy.all import sniff, sendp, hexdump, get_if_list, get_if_hwaddr

from p4utils.utils.helper import load_topo

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


def concat_bytes(byte_list):
    head = byte_list[0]
    for b in byte_list[1:]:
        head = (head << 8) | b
    return head


def int2ip(ip_int):
    return socket.inet_ntoa(struct.pack('I', socket.htonl(ip_int)))


def extract_header(header, ip_coverter=None):
    if ip_coverter is None:
        topo = load_topo("topology.json")

        def ip_coverter(ip):
            # return topo.ip_to_host[int2ip(ip)]['name']  # ip to host name
            try:
                return topo.ip_to_host[int2ip(ip)]['name']  # ip to host name
            except:
                print(ip)
                return ip

    data = {}
    for field in header.fields_desc:
        if 'resv' in field.name:
            continue

        value = getattr(header, field.name)
        if field.name.endswith('ip'):
            value = ip_coverter(value)
        data[field.name] = value
    return data


def extract_header_list(header, ip_coverter=None, reverse=True):
    data = []
    item_name = header.fields_desc[0].name
    for item in getattr(header, item_name):
        if item.name == 'Raw':
            print("break", item)
            break

        item_data = extract_header(item, ip_coverter)

        if reverse:
            data.insert(0, item_data)
        else:
            data.append(item_data)
    return data


def get_header_size(hdr_t):
    return int(sum([field.size for field in hdr_t.fields_desc]) / 8)


class Receive():

    def __init__(self, iface, simple=False):
        self.topo = load_topo("topology.json")
        self.iface = iface
        self.count = 0
        self.option2parser = {
            27: self.parse_notice,
            28: self.parse_latency,
            29: self.parse_report,
            31: self.parse_INT,
            0: self.parse_normal,
        }

        self.simple = simple
        self.verbose = not simple
        self.headers = []

        ifaddresses = netifaces.ifaddresses(iface)
        if iface.startswith('s'):
            self.local_ip = ""
        else:
            self.local_ip = ifaddresses[netifaces.AF_INET][0]['addr']
        print("IP", self.local_ip)

    def parse_header(self, hdr_t, item_t=None, count=1):
        if item_t is None:
            offset = get_header_size(hdr_t)
        else:
            hs = get_header_size(item_t)
            offset = hs * count
        offset = int(offset)
        hdr = hdr_t(self.raw_load[:offset])
        self.raw_load = self.raw_load[offset:]

        self.headers.append(hdr)

        if self.verbose:
            print(hdr.name, "-> left", len(self.raw_load))

        return hdr

    def show_all(self):
        if self.verbose:
            for header in self.headers:
                header.show()
            print("payload:", "".join(map(chr, bytes(self.raw_load))))

    def extract_header_list(self, header, name=None):
        if name is None:
            name = header.name
        self.data_json[name] = extract_header_list(header)

    def parse_debug_header(self, show=True):
        debug_shim = self.parse_header(debug_shim_header)
        debug = self.parse_header(debug_header,
                                  debug_item,
                                  count=debug_shim.count)

        self.extract_header_list(debug)

        # self.headers += [debug_shim, debug]

        return debug_shim, debug

    def parse_notice(self, pkt):
        print("parse Notice")

        option_data = IPv4_option_value(pkt['IP'].options[0].value)
        option_data.show()

        if 'Raw' in pkt:
            self.raw_load = pkt['Raw'].load
            print(len(self.raw_load))

            if (DEBUG):
                debug_shim, debug = self.parse_debug_header()
                print(len(self.raw_load))
            print("payload", self.raw_load)
        else:
            print("No Payload")

    def parse_report(self, pkt):
        print("Parse Report")
        self.raw_load = pkt['Raw'].load

        option_data = IPv4_option_value(pkt['IP'].options[0].value)
        self.headers.append(option_data)
        self.data_json['path_id'] = option_data.path_id

        report_count = option_data.src_count
        reports = self.parse_header(INT_report_header,
                                    report_item,
                                    count=report_count)
        # self.extract_header_list(reports)

        # if (DEBUG):
        #     debug_shim, debug = self.parse_debug_header()

        print(self.raw_load)

    def parse_latency(self, pkt):
        print("Parse Latency")
        self.raw_load = self._get_raw_bytes(pkt)

        option_data = IPv4_option_value(pkt['IP'].options[0].value)
        self.headers.append(option_data)

        latency_shim = self.parse_header(latency_shim_header)
        self.data_json['latency_shim'] = extract_header(latency_shim,
                                                        ip_coverter=int2ip)
        self.data_json['latency_shim']['count'] = option_data.src_count

        latency = self.parse_header(latency_header, latency_item, count=8)
        self.data_json['latency'] = [
            l['latency'] for l in extract_header_list(latency, reverse=False)
        ]
        if self.verbose:
            latency_shim.show()
            latency.show()

        if (DEBUG):
            debug_shim, debug = self.parse_debug_header()
            if self.verbose:
                debug_shim.show()
                debug.show()

    def _get_raw_bytes(self, pkt):
        if pkt.haslayer('UDP'):
            print(pkt['UDP'])
            print(bytes(pkt['UDP'])[8:])
            # print(pkt['UDP'].load)
            raw_load = bytes(pkt['UDP'])[8:]
            # ipdb.set_trace()
        elif pkt.haslayer('TCP'):
            # self.raw_load = pkt['TCP'].load
            raw_load = bytes(pkt['TCP'])[20:]
        return raw_load

    def parse_INT(self, pkt):
        print("Bussiness pkt with INT tag")
        # if pkt.haslayer('Raw'):
        #     self.raw_load = pkt['Raw'].load
        # else:
        if pkt.haslayer('UDP'):
            print(pkt['UDP'])
            print(bytes(pkt['UDP'])[8:])
            # print(pkt['UDP'].load)
            self.raw_load = bytes(pkt['UDP'])[8:]
            # ipdb.set_trace()
        elif pkt.haslayer('TCP'):
            # self.raw_load = pkt['TCP'].load
            self.raw_load = bytes(pkt['TCP'])[20:]
        print(len(self.raw_load))

        option_data = IPv4_option_value(pkt['IP'].options[0].value)
        self.headers.append(option_data)

        int_shim = self.parse_header(INT_shim_header)

        if (DEBUG):
            debug_shim, debug = self.parse_debug_header()

        self.data_json.update(extract_header(option_data))
        self.data_json.update(extract_header(int_shim))
        # import ipdb
        # ipdb.set_trace()
        self.data_json.update(
            dict(src_port=pkt['UDP'].sport
                 if pkt.haslayer("UDP") else pkt['TCP'].sport,
                 dst_port=pkt['UDP'].dport
                 if pkt.haslayer("UDP") else pkt['TCP'].dport,
                 protocol=pkt['IP'].proto))

        self.show_all()

    def parse_normal(self, pkt):
        option_data = pkt['IP'].options[0]

        self.data_json.update(
            dict(
                src_count=option_data.src_count,
                path_id=option_data.path_id,
            ))

        pprint(self.data_json)

    def handle_pkt(self, pkt):
        self.headers = []
        receive_t = int(time.monotonic() * 1e8)  # timestamp

        if pkt['Ethernet'].dst == 'ff:ff:ff:ff:ff:ff':  # sender
            print("boardcast packet from {} to {}".format(
                pkt['IP'].src, pkt['IP'].dst))
            # parse packet
            self.data_json = dict(
                src_ip=self.topo.ip_to_host[pkt['IP'].src]['name'],
                dst_ip=self.topo.ip_to_host[pkt['IP'].dst]['name'],
                receive_t=receive_t,
            )

            print()
            print(hexdump(pkt))
            print()

            if len(pkt['IP'].options) > 0:
                option_flag = pkt['IP'].options[0].option
                if option_flag in self.option2parser:
                    parser_func = self.option2parser[option_flag]
                    parser_func(pkt)
            else:
                option_flag = "none"

            with open(f"log/hosts/{self.iface}-{option_flag}.json", "a+") as f:
                f.write(json.dumps(self.data_json) + ",\n")
            print("==" * 30)
        elif pkt.haslayer("IP") and pkt['IP'].dst != self.local_ip:
            print("send packet from {} to {}".format(pkt['IP'].src,
                                                     pkt['IP'].dst))
        else:
            if not self.simple:
                print("\nreceive a packet:")
                pkt.show2(indent=2)
                # print hexdump(pkt.payload.payload.payload)
                print("parse INT switch traces")
                print("=" * 20)

            # parse packet
            self.data_json = dict(
                src_ip=self.topo.ip_to_host[pkt['IP'].src]['name'],
                dst_ip=self.topo.ip_to_host[pkt['IP'].dst]['name'],
                receive_t=receive_t,
            )

            print()
            print(hexdump(pkt))
            print()

            if len(pkt['IP'].options) > 0:
                option_flag = pkt['IP'].options[0].option
                if option_flag in self.option2parser:
                    parser_func = self.option2parser[option_flag]
                    parser_func(pkt)
            else:
                option_flag = "none"

            with open(f"log/hosts/{self.iface}-{option_flag}.json", "a+") as f:
                f.write(json.dumps(self.data_json) + ",\n")
            print("==" * 30)

        sys.stdout.flush()


def main():
    args = get_args()
    iface = args.iface

    print("sniffing on %s" % iface)

    receive = Receive(iface, args.simple)

    # filter = "udp and port 4321"
    filter = "ip and (tcp or udp)"
    print(filter)

    sys.stdout.flush()
    sniff(
        filter=filter,
        #   lfilter=lambda d: d.dst == 'ff:ff:ff:ff:ff:ff',
        iface=iface,
        prn=lambda x: receive.handle_pkt(x))
    # sniff(iface=iface, prn=lambda x: receive.handle_pkt(x))


if __name__ == '__main__':
    main()
