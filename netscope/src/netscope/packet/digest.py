import nnpy
import struct
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
import os, sys
from pprint import pprint
import json
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from headers import report_item, latency_shim_header, latency_header, latency_item, INT_report_header
from receive import extract_header_list, extract_header, get_header_size


class Digest():

    def __init__(self, sw_name):
        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)

    def unpack_digest(self, msg, num_samples):
        # print("digest")
        # sys.stdout.flush()
        digest = []
        msg = msg[32:]  # digest header
        return digest

    def recv_msg_digest(self, msg):
        # print(msg)
        sys.stdout.flush()
        topic, device_id, ctx_id, list_id, buffer_id, num = struct.unpack(
            "<iQiiQi", msg[:32])
        # print(topic, device_id, ctx_id, list_id, buffer_id, num)
        digest = self.unpack_digest(msg, num)
        # Acknowledge digest back to switch
        self.controller.client.bm_learning_ack_buffer(ctx_id, list_id,
                                                      buffer_id)

    def run_digest_loop(self):
        sub = nnpy.Socket(nnpy.AF_SP, nnpy.SUB)
        notifications_socket = self.controller.client.bm_mgmt_get_info(
        ).notifications_socket
        sub.connect(notifications_socket)
        sub.setsockopt(nnpy.SUB, nnpy.SUB_SUBSCRIBE, '')
        print(f"Listening on {self.sw_name}'s digest.")
        sys.stdout.flush()
        while True:
            msg = sub.recv()
            self.receive_t = int(time.monotonic() * 1e8)
            # print(msg)
            self.recv_msg_digest(msg)


class ReportDigest(Digest):

    def __init__(self, sw_name):
        super().__init__(sw_name)
        self.log_dir = 'log/hosts'

    def unpack_digest(self, msg, num_samples):
        msg = msg[32:]  # digest header
        report_hdr = INT_report_header(msg)
        reports = extract_header_list(report_hdr)
        for report in reports:
            # report['receive_t'] = self.receive_t
            report['receive_t'] = int(time.monotonic() * 1e8)
        self.log(reports)

    def log(self, reports):
        with open(os.path.join(self.log_dir, f"{self.sw_name}.json"),
                  'a+') as f:
            f.write(json.dumps(reports).strip('[]') + ",\n")


if __name__ == "__main__":
    import sys
    sw_name = sys.argv[1]
    controller = ReportDigest(sw_name).run_digest_loop()
