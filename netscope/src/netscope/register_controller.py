from routing_controller import Controller
import numpy as np
import re
import os, sys, time
import subprocess

from scapy.all import Packet, PacketListField, BitField

from packet.digest import Digest
# from packet.headers import INT_report_header
from packet.receive import extract_header_list

reg_names = [
    "buffer_src_tstamp", "buffer_latency", "buffer_src_ip", "buffer_dst_ip",
    "buffer_path_count", "buffer_flow_count", "buffer_flow_drop",
    "buffer_qdepth", "buffer_path_pkt_size", "buffer_path_id",
    "buffer_flow_src_epoch_gap"
]


class report_item(Packet):
    name = "INT_report_item"
    fields_desc = [
        BitField("src_ip", 0, 32),
        BitField("dst_ip", 0, 32),
        BitField("src_port", 0, 16),
        BitField("dst_port", 0, 16),
        BitField("protocol", 0, 8),
        BitField("latency", 0, 48),
    ]

    def extract_padding(self, p):
        return "", p


class INT_report_header(Packet):
    name = "INT_report"
    fields_desc = [PacketListField("reports", [], report_item)]


class RegisterController(Controller, Digest):

    def __init__(self):
        Controller.__init__(self, init=False)
        Digest.__init__(self, self.collector_sw)
        self.sleep_t = 2

        self.read_counter = -1
        self.connect_to_switches()
        self.csv_path = "log/reg.csv"
        self.last_read_t = 0

        # if not os.path.exists(self.csv_path):
        with open(self.csv_path, "w") as f:
            reg_col = ",".join(
                map(lambda x: re.sub(r"^buffer_", "", x), reg_names))
            f.write(f"sw,index,{reg_col},read_counter\n")

    def _get_buffer_index(self, sw):
        return self.controllers[sw].register_read("buffer_index_reg", 0)

    def read(self):
        self.last_read_t = int(time.monotonic() * 1e8)  # timestamp
        print(self.last_read_t)
        self.read_counter += 1
        content = ""
        for sw in self.topo.get_p4switches():
            if sw == self.collector_sw: continue
            try:
                index = self._get_buffer_index(sw)  # index that to be wirte
                print(sw, "index", index)

                regs = [
                    self.controllers[sw].register_read(name)
                    for name in reg_names
                ]

                [  # reset all register
                    self.controllers[sw].register_reset(name)
                    for name in reg_names + ['buffer_index_reg']
                ]

                regs = [",".join(map(str, l)) for l in np.array(regs).T]

                i = index
                # iter each index (csv sline)
                for i in range(index, len(regs)):
                    if regs[i].startswith("0"):
                        break
                    content += f"{sw},{i},{regs[i]},{self.read_counter}\n"
                for i in range(index):
                    if regs[i].startswith("0"):
                        continue
                    content += f"{sw},{i},{regs[i]},{self.read_counter}\n"
            except Exception as e:
                print(e)

        with open(self.csv_path, "a+") as f:
            f.write(content)

    def unpack_digest(self, msg, num_samples):
        msg = msg[32:]  # digest header
        receive_t = int(time.monotonic() * 1e8)  # timestamp
        print("receive_t", receive_t)
        if receive_t - self.last_read_t > 1e9 / 1e0:
            print("read!")
            self.read()
        else:
            print("not read yet")
        report_hdr = INT_report_header(msg)
        reports = extract_header_list(report_hdr)
        print(reports)
        sys.stdout.flush()


if __name__ == "__main__":
    RC = RegisterController()
    RC.run_digest_loop()