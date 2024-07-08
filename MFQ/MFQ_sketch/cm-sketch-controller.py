import socket, struct, pickle, os
from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_thrift_API import *
from crc import Crc

# crc32_polinomials = [0x04C11DB7, 0xEDB88320, 0xDB710641, 0x82608EDB, 0x741B8CD7, 0xEB31D82E,
#                      0xD663B05, 0xBA0DC66B, 0x32583499, 0x992C1A4C, 0x32583499, 0x992C1A4C]
QUANTILE_PHI = "0.9_64KB"
crc16_polinomials = [0x14C1, 0xEDB8, 0xDB71, 0x8260, 0x741B, 0xEB31,
                     0xD660, 0xBA0D, 0x3258, 0x992C, 0x3258, 0x992C]

class CMSController(object):

    def __init__(self, sw_name, set_hash):

        self.topo = load_topo('topology.json')
        self.sw_name = sw_name
        self.set_hash = set_hash
        self.thrift_port = self.topo.get_thrift_port(sw_name)
        self.controller = SimpleSwitchThriftAPI(self.thrift_port)
        print(self.thrift_port)
        self.custom_calcs = self.controller.get_custom_crc_calcs()
        print(self.custom_calcs)
        self.register_num =  len(self.custom_calcs)
        

        self.init()
        self.registers = []

    def init(self):
        if self.set_hash:
            print("set_hashes")
            self.set_crc_custom_hashes()
            # self.set_percentile_result()
        print("init")
        self.create_hashes()

    def set_percentile_result(self):
        self.controller.table_clear("percentile_match")
        self.controller.table_add("percentile_match","set_percentile_result", ["1->5"],["0"])
        self.controller.table_add("percentile_match","set_percentile_result", ["5->15"],["1"])




    def set_forwarding(self):
        self.controller.table_add("forwarding", "set_egress_port", ['1'], ['2'])
        self.controller.table_add("forwarding", "set_egress_port", ['2'], ['1'])

    def reset_registers(self):
        for i in range(self.register_num):
            self.controller.register_reset("prev_lat_ts_sketch{}".format(i))
            self.controller.register_reset("max_gap_sketch{}".format(i))
            self.controller.register_reset("min_gap_sketch{}".format(i))
            self.controller.register_reset("count_sketch{}".format(i))
            self.controller.register_reset("debug_count_sketch{}".format(i))
            self.controller.register_reset("ingr_ts_sketch{}".format(i))
            self.controller.register_reset("egr_ts_sketch{}".format(i))
            self.controller.register_reset("lat_quantile_sketch{}".format(i))
            self.controller.register_reset("c_plus_sketch{}".format(i))
            self.controller.register_reset("c_minus_sketch{}".format(i))
            self.controller.register_reset("max_value_sketch{}".format(i))
            self.controller.register_reset("min_value_sketch{}".format(i))





    def flow_to_bytestream(self, flow):
        return socket.inet_aton(flow[0]) + socket.inet_aton(flow[1]) + struct.pack(">HHB",flow[2], flow[3], 6)

    def set_crc_custom_hashes(self):
        i = 0
        for custom_crc16, width in sorted(self.custom_calcs.items()):
            print("ii",i, custom_crc16,width, hex(crc16_polinomials[i]))
            self.controller.set_crc16_parameters(custom_crc16, crc16_polinomials[i], 0xffff, 0b1111111111111111, True, True)
            i+=1

    def create_hashes(self):
        self.hashes = []
        for i in range(self.register_num):
            self.hashes.append(Crc(16, crc16_polinomials[i], True, 0xffff, True, 0b1111111111111111))

    def read_registers(self):
        self.prev_ts_registers = []
        self.max_gap_registers = []
        self.min_gap_registers = []
        self.count_registers = []
        self.debug_registers = []
        self.ing_registers = []
        self.eg_registers = []
        self.c_plus_registers = []
        self.c_minus_registers = []
        self.lat_quantile_registers = []
        for i in range(self.register_num):
            self.prev_ts_registers.append(self.controller.register_read("prev_lat_ts_sketch{}".format(i)))
            self.max_gap_registers.append(self.controller.register_read("max_gap_sketch{}".format(i)))
            self.min_gap_registers.append(self.controller.register_read("min_gap_sketch{}".format(i)))
            self.count_registers.append(self.controller.register_read("count_sketch{}".format(i)))
            self.debug_registers.append(self.controller.register_read("debug_count_sketch{}".format(i)))
            self.ing_registers.append(self.controller.register_read("ingr_ts_sketch{}".format(i)))
            self.eg_registers.append(self.controller.register_read("egr_ts_sketch{}".format(i)))
            self.c_plus_registers.append(self.controller.register_read("c_plus_sketch{}".format(i)))
            self.c_minus_registers.append(self.controller.register_read("c_minus_sketch{}".format(i)))
            self.lat_quantile_registers.append(self.controller.register_read("lat_quantile_sketch{}".format(i)))
            




        print("prev_ts_registers:", self.prev_ts_registers)
        print("max_gap_registers:", self.max_gap_registers)
        print("min_gap_registers:", self.min_gap_registers)
        print("count_registers:", self.count_registers)
        print("debug_registers:", self.debug_registers)
        print("ing_registers:", self.ing_registers)
        print("eg_registers:", self.eg_registers)
        print("c_minus_registers:", self.c_minus_registers)
        print("c_plus_registers:",self.c_plus_registers)
        print("lat_quantile_registers:", self.lat_quantile_registers)



    def get_cms(self, flow, mod):
        values = []
        lat_quantile_values = []
        flow_counts_values = []
        for i in range(self.register_num):
            index = self.hashes[i].bit_by_bit_fast(self.flow_to_bytestream(flow)) % mod
            print(flow, i, index)
            print("index:{}, prev_ts:{}, max_gap:{}, min_gap:{}, count:{}, debug:{}".format(index,\
                self.prev_ts_registers[i][index], self.max_gap_registers[i][index], self.min_gap_registers[i][index], \
                           self.count_registers[i][index], self.debug_registers[i][index]))
            values.append([self.prev_ts_registers[i][index], self.max_gap_registers[i][index], self.min_gap_registers[i][index], \
                           self.count_registers[i][index], self.debug_registers[i][index]])
            lat_quantile_values.append(self.lat_quantile_registers[i][index])
            flow_counts_values.append(self.count_registers[i][index])
        print("---------")
        
        return lat_quantile_values,flow_counts_values
        # return min(values)

    def decode_registers(self, eps, n, mod, ground_truth_file="sent_flows.pickle"):

        """In the decoding function you were free to compute whatever you wanted.
           This solution includes a very basic statistic, with the number of flows inside the confidence bound.
        """
        
        self.read_registers()
        confidence_count = 0
        if ground_truth_file == "sent_flows.pickle":
            flow_dataset_name = "mimic"
            flows = pickle.load(open(ground_truth_file, "rb"))
            # print(flows)
        elif ground_truth_file == "sent_flows_webget_2016.pickle":
            flow_dataset_name = ground_truth_file.split(".")[0].split("_")[2]
            flows = pickle.load(open(ground_truth_file,"rb"))
        elif ground_truth_file == "sent_flows_seattle.pickle":
            flow_dataset_name = ground_truth_file.split(".")[0].split("_")[-1]
            flows = pickle.load(open(ground_truth_file,"rb"))
        elif ground_truth_file == "sent_flows_synthetic.pickle":
            flow_dataset_name = ground_truth_file.split(".")[0].split("_")[-1]
            flows = pickle.load(open(ground_truth_file,"rb"))
        # print(flows)
        estimate_quantile = {}
        for flow, n_packets in flows.items():
            print("~~~~~~~~~~~~~~~~~~~~~begin:")
            # print(flow, n_packets)
            cms = self.get_cms(flow, mod)
            estimate_quantile[flow] = cms #quantile 和 flow_count
            print("Packets sent and read by the cms: {}/{}".format(n_packets, cms))
            print("~~~~~~~~~~~~~~~~~~~~~end")
            # if not (cms <(n_packets + (eps*n))):
            #     confidence_count +=1
        with open("log/hosts/sent_flow_quantile.pickle","wb") as f:
            pickle.dump(estimate_quantile, f)
        with open("../exp_results/MFQ/{}/sent_flows_quantile_{}.pickle".format(flow_dataset_name, QUANTILE_PHI), "wb") as f:
            pickle.dump(estimate_quantile, f)
        print("Not hold for {}%".format(float(confidence_count)/len(flows)*100))

    def dump_table(self):
        self.controller.table_dump("percentile_match")
        



if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sw', help="switch name to configure" , type=str, required=False, default="s1")
    parser.add_argument('--eps', help="epsilon to use when checking bound", type=float, required=False, default=0.01)
    parser.add_argument('--n', help="number of packets sent by the send.py app", type=int, required=False, default=1000)
    parser.add_argument('--mod', help="number of cells in each register", type=int, required=False, default=4096)
    parser.add_argument('--flow-file', help="name of the file generated by send.py", type=str, required=False, default="sent_flows.pickle")
    parser.add_argument('--option', help="controller option can be either set_hashes, decode or reset registers", type=str, required=False, default="set_hashes")
    args = parser.parse_args()

    set_hashes = args.option == "set_hashes"
    controller = CMSController(args.sw, set_hashes)

    if args.option == "decode":
        import time
        start_time = time.time()  # 记录开始时间
        controller.decode_registers(args.eps, args.n, args.mod, args.flow_file)
        end_time = time.time()    # 记录结束时间
        execution_time = end_time - start_time
        print("Function execution time:", execution_time, "seconds")

    elif args.option == "reset":
        print("reseting....")
        controller.reset_registers()
    elif args.option == "dump":
        controller.dump_table()
