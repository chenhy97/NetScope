#!/usr/bin/env python3
import socket
import random
import os
import struct
import fcntl
import time
import pickle
import codecs
from time import sleep

# checksum functions needed for calculation checksum
def checksum(msg):
    s = 0
    # loop taking 2 characters at a time
    for i in range(0, len(msg), 2):
        w = (msg[i] << 8) + msg[i+1]
        s = s + w

    s = (s>>16) + (s & 0xffff)
    #s = s + (s >> 16)    #complement and mask to 4 byte short
    s = ~s & 0xffff

    return s

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


def eth_header(src, dst, proto=0x0800):
    src_bytes = b"".join([codecs.decode(x,'hex') for x in src.split(":")])
    dst_bytes = b"".join([codecs.decode(x,'hex') for x in dst.split(":")])
    return src_bytes + dst_bytes + struct.pack("!H", proto)
def lat_header(latency):
    latency_byte_stream = latency.to_bytes(6, byteorder='big', signed=False)
    return struct.pack("6s", latency_byte_stream)
def ip_header(src,dst,ttl,proto,id=0):

    # now start constructing the packet
    packet = ''
    # ip header fields
    ihl = 5
    version = 4
    tos = 128
    tot_len = 20 + 20   # python seems to correctly fill the total length, dont know how ??
    frag_off = 0
    if proto == "tcp":
        proto = socket.IPPROTO_TCP
    elif proto == "udp":
        proto = socket.IPPROTO_UDP
    else:
        print("proto unknown")
        return
    check = 10  # python seems to correctly fill the checksum
    saddr = socket.inet_aton ( src )  #Spoof the source ip address if you want to
    daddr = socket.inet_aton ( dst )

    ihl_version = (version << 4) + ihl

    # the ! in the pack format string means network order
    ip_header = struct.pack('!BBHHHBBH4s4s' , ihl_version, tos, tot_len, id, frag_off, ttl, proto, check, saddr, daddr)
    return ip_header

def tcp_header(src,dst,sport,dport):

    # tcp header fields
    source = sport #sourceport
    dest = dport  # destination port
    seq = 0
    ack_seq = 0
    doff = 5    #4 bit field, size of tcp header, 5 * 4 = 20 bytes
    #tcp flags
    fin = 0
    syn = 1
    rst = 0
    psh = 0
    ack = 0
    urg = 0
    window = socket.htons (5840)    #   maximum allowed window size
    check = 0
    urg_ptr = 0

    offset_res = (doff << 4) + 0
    tcp_flags = fin + (syn << 1) + (rst << 2) + (psh <<3) + (ack << 4) + (urg << 5)

    # the ! in the pack format string means network order
    tcp_header = struct.pack('!HHLLBBHHH' , source, dest, seq, ack_seq, offset_res, tcp_flags,  window, check, urg_ptr)

    # pseudo header fields
    source_address = socket.inet_aton( src )
    dest_address = socket.inet_aton(dst)
    placeholder = 0
    proto = socket.IPPROTO_TCP
    tcp_length = len(tcp_header)

    psh = struct.pack('!4s4sBBH' , source_address , dest_address , placeholder , proto , tcp_length)
    psh = psh + tcp_header

    tcp_checksum = checksum(psh)

    # make the tcp header again and fill the correct checksum
    tcp_header = struct.pack('!HHLLBBHHH' , source, dest, seq, ack_seq, offset_res, tcp_flags,  window, tcp_checksum , urg_ptr)

    # final full packet - syn packets dont have any data
    return tcp_header

def getInterfaceName():
    #assume it has eth0

    return [x for x in os.listdir('/sys/cla'
                                  'ss/net') if "eth0" in x][0]

def send_n(s, packet, n):
    for _ in range(n):
        s.send(packet)
        time.sleep(0.01)
def send_n_with_latency(s, packets, n):
    for i in range(n):
        s.send(packets[i])
        time.sleep(0.01)

def create_packet_ip_tcp(eth_h, src_ip, dst_ip, sport, dport):
    return eth_h + ip_header(src_ip, dst_ip, 64, "tcp",1) + tcp_header(src_ip, dst_ip, sport, dport)

def create_packets_ip_tcp_with_latency(n, flow_latency, eth_h, src_ip, dst_ip, sport, dport):
    packets = []
    for i in range(n):
        packet = eth_h + ip_header(src_ip, dst_ip, 64, "tcp",1) + tcp_header(src_ip, dst_ip, sport, dport) + lat_header(flow_latency[i])
        # print((flow_latency[i]))
        packets.append(packet)
    return packets

def get_random_flow():
    src_ip = socket.inet_ntoa(struct.pack("!I", random.randint(167772160, 4261412864)))
    dst_ip = socket.inet_ntoa(struct.pack("!I", random.randint(167772160, 4261412864)))
    sport = random.randint(1, 2 ** 16 - 2)
    dport = random.randint(1, 2 ** 16 - 2)
    return (src_ip, dst_ip, sport, dport)

def generate_test(n_packets, n_heavy_hitters, n_normal_flows, percentage_n_heavy_hitters=0.9):

    normal_flows = {}
    heavy_hitters = {}

    #create heavy hitters:
    for _ in range(n_heavy_hitters):
        flow = get_random_flow()
        #check the flow does not exist
        while flow in heavy_hitters:
            flow = get_random_flow()
        heavy_hitters[flow] = 0

    #create heavy hitters:
    for _ in range(n_normal_flows):
        flow = get_random_flow()
        #check the flow does not exist
        while (flow in heavy_hitters or flow in normal_flows):
            flow = get_random_flow()
        normal_flows[flow] = 0

    for _ in range(n_packets):
        p = random.uniform(0,1)

        #increase heavy hitters
        if p <= percentage_n_heavy_hitters:
            flow = random.choice(list(heavy_hitters.keys()))
            heavy_hitters[flow] +=1

        #increase normal flows
        else:
            flow = random.choice(list(normal_flows.keys()))
            normal_flows[flow] +=1

    return heavy_hitters, normal_flows

def save_flows(flows):
    with open("sent_flows.pickle", "wb") as f:
        pickle.dump(flows, f)
def load_flows():
    with open("sent_flows.pickle", "rb") as f:
        flows = pickle.load( f)
    return flows
def load_flows_latency(filename):
    if filename == "./log/hosts/h2-eth0.json":
        with open("./log/hosts/h2-eth0.json") as f:
            lines = f.readlines()
            flow_latency = {}
            for line in lines:
                line = eval(line)
                flow = (line["src_ip"],line['dst_ip'],line['sport'],line['dport'])
                lat = line["latency"]
                if flow not in flow_latency.keys():
                    flow_latency[flow] = []
                flow_latency[flow].append(int(lat))
        return flow_latency
    elif filename == "webget_2016.csv":
        import pandas as pd
        flow_data = pd.read_csv(filename).groupby(["src_ip","dst_ip", "sport","dport"])["latency"].agg(list)
        flow_latency = {}
        for key, value_list in flow_data.items():
            flow_latency[tuple(key)] = value_list
        return flow_latency
    elif filename == "seattle_data.csv" or filename == "synthetic_data.csv":
        import pandas as pd
        flow_data = pd.read_csv(filename)
        flow_latency = {}
        for column  in flow_data.columns:
            src = column.split("->")[0]
            dst = column.split("->")[1]
            key_tuple = (src,dst,1234,5678)
            column_data = flow_data[column].values
            flow_latency[key_tuple] = (column_data).tolist()
        return flow_latency
def main(n_packets, n_heavy_hitters, n_small_flows, p_heavy_hitter):

    send_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    intf_name = getInterfaceName()
    send_socket.bind((intf_name, 0))

    eth_h = eth_header("01:02:20:aa:33:aa", "02:02:20:aa:33:aa", 0x800)
    heavy_hitters, small_flows = generate_test(n_packets, n_heavy_hitters, n_small_flows, p_heavy_hitter)

    #merge
    heavy_hitters.update(small_flows)
    flows = heavy_hitters.copy()
    print(flows)

    #save flows in a file so the controller can compare
    save_flows(flows)

    for flow, n in flows.items():
        packet = create_packet_ip_tcp(eth_h, *flow)
        send_n(send_socket, packet, n)
        
    send_socket.close()

def main_read_file(filename, n_packets, n_heavy_hitters):
    send_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    intf_name = getInterfaceName()
    send_socket.bind((intf_name, 0))

    eth_h = eth_header("01:02:20:aa:33:aa", "02:02:20:aa:33:aa", 0x800)
    flows_latency= load_flows_latency(filename)
    if filename == "h2-eth0.json":
        flows = load_flows()

        for flow, n in flows.items():
            packets = create_packets_ip_tcp_with_latency(n, flows_latency[flow], eth_h, *flow)
            send_n_with_latency(send_socket, packets, n)
    elif filename == "webget_2016.csv":
        packets_per_flow = int(n_packets/n_heavy_hitters)
        print(packets_per_flow)
        idx = 0
        loop_len = n_heavy_hitters if len(flows_latency.keys()) > n_heavy_hitters else len(flows_latency.keys())
        sent_flow = {}
        for flow in  flows_latency.keys():
            if idx >= n_heavy_hitters:
                break
            if packets_per_flow > len(flows_latency[flow]):
                # print(len(flows_latency[flow]))
                continue
            n =  packets_per_flow
            sent_flow[flow] = n
            packets = create_packets_ip_tcp_with_latency(n, flows_latency[flow], eth_h, *flow)
            send_n_with_latency(send_socket, packets, n)
            idx += 1
            print(idx,flow,n)
        with open("sent_flows_webget_2016.pickle", "wb") as f:
            pickle.dump(sent_flow, f)
    elif filename == "seattle_data.csv" or filename == "synthetic_data.csv":
        packets_per_flow = int(n_packets/n_heavy_hitters)
        print(packets_per_flow)
        idx = 0
        sent_flow = {}
        for flow in  flows_latency.keys():
            if idx >= n_heavy_hitters:
                break
            n =  packets_per_flow
            sent_flow[flow] = n
            packets = create_packets_ip_tcp_with_latency(n, flows_latency[flow], eth_h, *flow)
            send_n_with_latency(send_socket, packets, n)
            idx += 1
            print(idx,flow,n)
        if filename == "seattle_data.csv":
            with open("sent_flows_seattle.pickle", "wb") as f:
                pickle.dump(sent_flow, f)
        elif filename == "synthetic_data.csv":
            print(filename)
            with open("sent_flows_synthetic.pickle", "wb") as f:
                pickle.dump(sent_flow, f)
    send_socket.close()


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--n-pkt', help='number of packets', type=int, required=False, default=5000)
    parser.add_argument('--n-hh', help='number of heavy hitters', type=int, required=False, default=10)
    parser.add_argument('--n-sfw', help='number of small flows', type=int, required=False, default=990)
    parser.add_argument('--p-hh', help='percentage of packets sent by heavy hitters',type=float, required=False, default=0.95)
    parser.add_argument("--replay", help = "replay packets send", type=str, required=False, default = "history")
    args= parser.parse_args()
    if args.replay == "history":
        main_read_file("h2-eth0.json",_,_)
    elif args.replay == "webget":
        main_read_file("webget_2016.csv",args.n_pkt, args.n_hh)
    elif args.replay == "seattle":
        main_read_file("seattle_data.csv",args.n_pkt, args.n_hh)
    elif args.replay == "synthetic":
        main_read_file("synthetic_data.csv",args.n_pkt, args.n_hh)
    else:
        main(args.n_pkt, args.n_hh, args.n_sfw, args.p_hh)


