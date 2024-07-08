import json
import os
import pandas as pd
import fnmatch
import numpy as np
def read_from_latency_file(base_dir):
    import json
    file_name = base_dir + "hosts/h0-eth0-26.json"
    # 读取文件内容
    with open(file_name, 'r') as file:
        content = file.read()
    # 假设文件内容的多个JSON对象之间有明确的分隔符，如换行符
    json_strings = content.strip().split('\n')

    # 存储所有解析后的数据
    data_list = []

    # 逐个解析每个JSON字符串
    for json_str in json_strings:
        if json_str[-1] == ",":
            json_str = json_str[:-1]
        # print(json_str)
        try:
            data = json.loads(json_str)
            data_list.append(data)
        except json.JSONDecodeError as e:
            print(json_str)
            print(f"Error decoding JSON: {e}")
            break
    raw_flow_latency = {}
    raw_flow_qunatile = {}
    for data in data_list:
        flow = data["quantile_report"]["src_ip"] + "_" +data["quantile_report"]["dst_ip"]
        if flow not in raw_flow_latency.keys():
            raw_flow_latency[flow] = []
            raw_flow_qunatile[flow] = []
        raw_flow_latency[flow].append(data["quantile_report"]["latency"])
        raw_flow_qunatile[flow].append(data["quantile_report"]["quantile_value_sketch0"])
    raw_flow_latency_dict =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_latency, orient='index').values.T, columns=list(raw_flow_latency.keys()))
    raw_flow_qunatile_dict =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_qunatile, orient='index').values.T, columns=list(raw_flow_qunatile.keys()))
    return raw_flow_latency_dict, raw_flow_qunatile_dict
# 打印解析后的数据
# for data in data_list:
#     print(data)
def read_json(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    json_strings = content.strip().split('\n')
    data_list = []
    for json_str in json_strings:
        data = json.loads(json_str.rstrip(","))
        data_list.append(data)
    return data_list
def read_from_int_file(base_dir):
    raw_flow_latency_dict, raw_flow_qunatile_dict = {}, {}
    raw_flow_c_plus_dict, raw_flow_c_minus_dict, raw_flow_count_dict, raw_flow_perc_dict = {}, {},{}, {}

    raw_flow_max_gap_dict, raw_flow_min_gap_dict, raw_flow_lambda_dict,raw_flow_prev_max_gap_dict = {}, {}, {},{}
    raw_flow_max_value_dict, raw_flow_min_value_dict = {}, {}
    raw_flow_recv_ts_dict, raw_flow_MARS_AD_dict = {},{}
    raw_flow_src_port_dict, raw_flow_dst_port_dict = {}, {}
    
    for root, _, files in os.walk(base_dir):
        for file in fnmatch.filter(files, '*31.json'):
            file_path = os.path.join(root, file)
            data_list = read_json(file_path)
            for data in data_list:
                flow = data["src_ip"] + "_" + data["dst_ip"]
                
                if flow not in raw_flow_latency_dict.keys():
                    raw_flow_latency_dict[flow] = []
                    raw_flow_qunatile_dict[flow] = []
                    raw_flow_c_plus_dict[flow] = []
                    raw_flow_c_minus_dict[flow] = []
                    raw_flow_count_dict[flow] = []
                    raw_flow_perc_dict[flow] = []
                    raw_flow_max_gap_dict[flow], raw_flow_min_gap_dict[flow], raw_flow_lambda_dict[flow],raw_flow_prev_max_gap_dict[flow] = [], [], [],[]
                    raw_flow_max_value_dict[flow], raw_flow_min_value_dict[flow] = [], []
                    raw_flow_recv_ts_dict[flow] = []
                    raw_flow_MARS_AD_dict[flow] = []
                    raw_flow_src_port_dict[flow] = []
                    raw_flow_dst_port_dict[flow] = []
                raw_flow_latency_dict[flow].append(data["latency"])
                raw_flow_qunatile_dict[flow].append(data["quantile_value_sketch0"])
                raw_flow_c_plus_dict[flow].append(data["c_plus_value_sketch0"])
                raw_flow_c_minus_dict[flow].append(data["c_minus_value_sketch0"])
                raw_flow_count_dict[flow].append(data["count_sketch0"])
                raw_flow_perc_dict[flow].append(data["percentile"])
                raw_flow_max_gap_dict[flow].append(data["max_gap_value_sketch0"])
                raw_flow_min_gap_dict[flow].append(data["min_gap_value_sketch0"])
                raw_flow_lambda_dict[flow].append(data["lambda"])
                raw_flow_prev_max_gap_dict[flow].append(data["prev_max_gap_value"])
                raw_flow_max_value_dict[flow].append(data["max_value"])
                raw_flow_min_value_dict[flow].append(data["min_value"])
                raw_flow_recv_ts_dict[flow].append(data["receive_t"])
                raw_flow_MARS_AD_dict[flow].append(data["AD"])
                raw_flow_src_port_dict[flow].append(data["src_port"])
                raw_flow_dst_port_dict[flow].append(data["dst_port"])
                
    return raw_flow_latency_dict, raw_flow_qunatile_dict,raw_flow_c_plus_dict, raw_flow_c_minus_dict, raw_flow_count_dict,\
     raw_flow_perc_dict,raw_flow_max_gap_dict, raw_flow_min_gap_dict, raw_flow_lambda_dict,raw_flow_prev_max_gap_dict,raw_flow_max_value_dict,\
     raw_flow_min_value_dict, raw_flow_recv_ts_dict,raw_flow_MARS_AD_dict, raw_flow_src_port_dict, raw_flow_dst_port_dict

def get_flows_df(base_dir):
    raw_flow_latency_dict, raw_flow_qunatile_dict,raw_flow_c_plus_dict, raw_flow_c_minus_dict, \
    raw_flow_count_dict, raw_flow_perc_dict,raw_flow_max_gap_dict, raw_flow_min_gap_dict, \
    raw_flow_lambda_dict,raw_flow_prev_max_gap_dict,raw_flow_max_value_dict, raw_flow_min_value_dict,\
        raw_flow_recv_ts_dict,raw_flow_MARS_AD_dict, raw_flow_src_port_dict, raw_flow_dst_port_dict = read_from_int_file(base_dir)

    raw_flow_latency_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_latency_dict, orient='index').values.T, columns=list(raw_flow_latency_dict.keys()))
    raw_flow_qunatile_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_qunatile_dict, orient='index').values.T, columns=list(raw_flow_qunatile_dict.keys()))

    raw_flow_c_plus_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_c_plus_dict, orient='index').values.T, columns=list(raw_flow_c_plus_dict.keys()))
    raw_flow_c_minus_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_c_minus_dict, orient='index').values.T, columns=list(raw_flow_c_minus_dict.keys()))
    raw_flow_count_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_count_dict, orient='index').values.T, columns=list(raw_flow_count_dict.keys()))
    raw_flow_perc_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_perc_dict, orient='index').values.T, columns=list(raw_flow_perc_dict.keys()))

    raw_flow_max_gap_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_max_gap_dict, orient='index').values.T, columns=list(raw_flow_max_gap_dict.keys()))
    raw_flow_min_gap_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_min_gap_dict, orient='index').values.T, columns=list(raw_flow_min_gap_dict.keys()))
    raw_flow_lambda_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_lambda_dict, orient='index').values.T, columns=list(raw_flow_lambda_dict.keys()))
    raw_flow_prev_max_gap_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_prev_max_gap_dict, orient='index').values.T, columns=list(raw_flow_prev_max_gap_dict.keys()))

    raw_flow_max_value_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_max_value_dict, orient='index').values.T, columns=list(raw_flow_max_value_dict.keys()))
    raw_flow_min_value_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_min_value_dict, orient='index').values.T, columns=list(raw_flow_min_value_dict.keys()))

    raw_flow_recv_ts_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_recv_ts_dict, orient='index').values.T, columns=list(raw_flow_recv_ts_dict.keys()))

    raw_flow_MARS_AD_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_MARS_AD_dict, orient='index').values.T, columns=list(raw_flow_MARS_AD_dict.keys()))

    raw_flow_src_port_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_src_port_dict, orient='index').values.T, columns=list(raw_flow_src_port_dict.keys()))
    raw_flow_dst_port_df =  pd.DataFrame(pd.DataFrame.from_dict(raw_flow_dst_port_dict, orient='index').values.T, columns=list(raw_flow_dst_port_dict.keys()))


    merge_flow_info_dict = merge_flow_info(raw_flow_latency_df, raw_flow_max_value_df, raw_flow_min_value_df, raw_flow_qunatile_df, raw_flow_recv_ts_df,raw_flow_MARS_AD_df, raw_flow_src_port_df, raw_flow_dst_port_df)
    return merge_flow_info_dict

def merge_flow_info(raw_flow_latency_df, raw_flow_max_value_df, raw_flow_min_value_df, raw_flow_qunatile_df, raw_flow_recv_ts_df, raw_flow_MARS_AD_df, raw_flow_src_port_df, raw_flow_dst_port_df):
    merge_flow_info_dict = {}
    for flow in raw_flow_latency_df.columns:
        merge_flow_info_dict[flow] = pd.concat([raw_flow_recv_ts_df[flow], raw_flow_latency_df[flow], raw_flow_qunatile_df[flow], raw_flow_max_value_df[flow], \
                                                raw_flow_min_value_df[flow], raw_flow_MARS_AD_df[flow], raw_flow_src_port_df[flow], raw_flow_dst_port_df[flow]],\
             axis = 1, keys = ['recv_ts', 'latency', 'quantile', 'max', 'min','MARS_AD', 'src_port', 'dst_port'])
        merge_flow_info_dict[flow]['MARS_AD'] = merge_flow_info_dict[flow]["MARS_AD"].fillna(0).astype(int)
    return merge_flow_info_dict

# drop_bw: max_ratio = 2.5, sigma = 1
# else: max_ratio = 1, sigma = 3
def calc_threshold(merge_flow_info_dict, max_ratio = 1, sigma = 3):
    for flow in merge_flow_info_dict.keys():
        merge_flow_info_dict[flow]['sigma'] = (merge_flow_info_dict[flow]['max']/max_ratio + merge_flow_info_dict[flow]['min']) / 4
        merge_flow_info_dict[flow]['threshold'] = merge_flow_info_dict[flow]['quantile'] + sigma * merge_flow_info_dict[flow]['sigma']
    return merge_flow_info_dict

# threshold_per_flow['h16_h13']
def anomaly_detection(merge_flow_info_dict, threshold_per_flow):
    for flow in threshold_per_flow.keys():
        threshold_per_flow[flow]['prev_threshold'] = merge_flow_info_dict[flow]['threshold'].shift(1)
        threshold_per_flow[flow]["pred_label"] = merge_flow_info_dict[flow]['latency'] > threshold_per_flow[flow]['prev_threshold']
    return threshold_per_flow
def get_injection_info(base_dir):
    import json
    if base_dir == './log/':
        file_name = base_dir + "hosts/answer.json"
    else:
        file_name = base_dir + "/answer.json"
    with open(file_name) as f:
        inject_info = json.load(f)
    return inject_info

def label_AD_true_label(AD_res, inject_info, self_defined_offset=8):
    fault_type = list(inject_info.keys())[0]
    for flow in AD_res.keys():
        AD_res[flow]["true_label"] = (AD_res[flow]['recv_ts'] > inject_info[fault_type][0]["inject_t"]) & (AD_res[flow]['recv_ts'] < inject_info[fault_type][0]["inject_t"] + (inject_info[fault_type][0]["timeout"]+self_defined_offset)*1e8)
    return AD_res


def calc_AD_label(AD_res):
    in_network_AD = []
    MARS_AD = []
    real_label = []
    array_length = 0
    for flow in AD_res.keys():
        array_length = len(AD_res[flow]["pred_label"])
        if 1 in AD_res[flow]["pred_label"]:
            in_network_AD = in_network_AD + AD_res[flow].index[AD_res[flow]["pred_label"] == 1].to_list()
            real_label = AD_res[flow]["true_label"].astype(int)
            MARS_AD = MARS_AD + AD_res[flow].index[AD_res[flow]["MARS_AD"] == 1].to_list()
            # print(flow, AD_res[flow].iloc[50:].index[AD_res[flow]["pred_label"].iloc[50:] == 1].to_list())
    in_network_AD = sorted(list(set(in_network_AD)))
    MARS_AD = sorted(list(set(MARS_AD)))
    
    in_network_AD_label = np.zeros(array_length, dtype=int)
    in_network_AD_label[in_network_AD] = 1
    MARS_AD_label = np.zeros(array_length, dtype=int)
    MARS_AD_label[MARS_AD] = 1
    return np.array(in_network_AD_label)[50:], np.array(MARS_AD_label)[50:], np.array(real_label)[50:]

def anomaly_detection_static_threshold(merge_flow_info_dict):
    AD_T_100 = []
    AD_T_500 = []
    AD_T_1000 = []
    AD_T_5000 = []
    array_length = 0
    for flow in merge_flow_info_dict.keys():
        array_length = len(merge_flow_info_dict[flow]["latency"])
        merge_flow_info_dict[flow]["100_T_AD"] = merge_flow_info_dict[flow]['latency'] > 100000
        merge_flow_info_dict[flow]["500_T_AD"] = merge_flow_info_dict[flow]['latency'] > 500000
        merge_flow_info_dict[flow]["1000_T_AD"] = merge_flow_info_dict[flow]['latency'] > 1000000
        merge_flow_info_dict[flow]["5000_T_AD"] = merge_flow_info_dict[flow]['latency'] > 5000000
        AD_T_100 = AD_T_100 + merge_flow_info_dict[flow].index[merge_flow_info_dict[flow]["100_T_AD"] == 1].to_list()
        AD_T_500 = AD_T_500 + merge_flow_info_dict[flow].index[merge_flow_info_dict[flow]["500_T_AD"] == 1].to_list()
        AD_T_1000 = AD_T_1000 + merge_flow_info_dict[flow].index[merge_flow_info_dict[flow]["1000_T_AD"] == 1].to_list()
        AD_T_5000 = AD_T_5000 + merge_flow_info_dict[flow].index[merge_flow_info_dict[flow]["5000_T_AD"] == 1].to_list()
    AD_T_100 = sorted(list(set(AD_T_100)))
    AD_T_1000 = sorted(list(set(AD_T_1000)))
    AD_T_500 = sorted(list(set(AD_T_500)))
    AD_T_5000 = sorted(list(set(AD_T_5000)))

    AD_T_100_label = np.zeros(array_length, dtype=int)
    AD_T_100_label[AD_T_100] = 1
    AD_T_500_label = np.zeros(array_length, dtype=int)
    AD_T_500_label[AD_T_500] = 1

    AD_T_1000_label = np.zeros(array_length, dtype=int)
    AD_T_1000_label[AD_T_1000] = 1
    AD_T_5000_label = np.zeros(array_length, dtype=int)
    AD_T_5000_label[AD_T_5000] = 1

    return np.array(AD_T_100_label)[50:], np.array(AD_T_500_label)[50:], np.array(AD_T_1000_label)[50:], np.array(AD_T_5000_label)[50:]

def calc_exp_AD_efficiency(base_dir, sketch_max_ratio = 1, sketch_sigma = 3, offset = 8):
    merge_flow_info_dict = get_flows_df(base_dir)
    AD_T_100_label, AD_T_500_label, AD_T_1000_label, AD_T_5000_label = anomaly_detection_static_threshold(merge_flow_info_dict)
    threshold_per_flow = calc_threshold(merge_flow_info_dict, sketch_max_ratio, sketch_sigma)
    AD_res = anomaly_detection(merge_flow_info_dict, threshold_per_flow)
    inject_info = get_injection_info(base_dir)
    AD_res = label_AD_true_label(AD_res, inject_info, self_defined_offset= offset)
    # return AD_res
    in_network_AD_label, MARS_AD_label, real_label = calc_AD_label(AD_res)
    MARS_f1, MARS_precision, MARS_recall, MARS_TP, MARS_TN, MARS_FP, MARS_FN = calc_seq(MARS_AD_label, real_label)
    print("MARS:")
    print("F1:{}, Precision:{}, Recall:{}, TP:{}, TN:{}, FP:{}, FN:{}".format(MARS_f1, MARS_precision, MARS_recall, MARS_TP, MARS_TN, MARS_FP, MARS_FN))

    SKETCH_f1, SKETCH_precision, SKETCH_recall, SKETCH_TP, SKETCH_TN, SKETCH_FP, SKETCH_FN = calc_seq(in_network_AD_label, real_label)
    print("Sketch based:")
    print("F1:{}, Precision:{}, Recall:{}, TP:{}, TN:{}, FP:{}, FN:{}".format(SKETCH_f1, SKETCH_precision, SKETCH_recall, SKETCH_TP, SKETCH_TN, SKETCH_FP, SKETCH_FN))


    T_100_f1, T_100_precision, T_100_recall, T_100_TP, T_100_TN, T_100_FP, T_100_FN = calc_seq(AD_T_100_label, real_label)
    # print("T_100:")
    # print("F1:{}, Precision:{}, Recall:{}, TP:{}, TN:{}, FP:{}, FN:{}".format(T_100_f1, T_100_precision, T_100_recall, T_100_TP, T_100_TN, T_100_FP, T_100_FN))

    T_1000_f1, T_1000_precision, T_1000_recall, T_1000_TP, T_1000_TN, T_1000_FP, T_1000_FN = calc_seq(AD_T_1000_label, real_label)
    # print("T_1000:")
    # print("F1:{}, Precision:{}, Recall:{}, TP:{}, TN:{}, FP:{}, FN:{}".format(T_1000_f1, T_1000_precision, T_1000_recall, T_1000_TP, T_1000_TN, T_1000_FP, T_1000_FN))

    T_500_f1, T_500_precision, T_500_recall, T_500_TP, T_500_TN, T_500_FP, T_500_FN = calc_seq(AD_T_500_label, real_label)
    # print("T_500:")
    # print("F1:{}, Precision:{}, Recall:{}, TP:{}, TN:{}, FP:{}, FN:{}".format(T_500_f1, T_500_precision, T_500_recall, T_500_TP, T_500_TN, T_500_FP, T_500_FN))

    T_5000_f1, T_5000_precision, T_5000_recall, T_5000_TP, T_5000_TN, T_5000_FP, T_5000_FN = calc_seq(AD_T_5000_label, real_label)
    # print("T_5000:")
    # print("F1:{}, Precision:{}, Recall:{}, TP:{}, TN:{}, FP:{}, FN:{}".format(T_5000_f1, T_5000_precision, T_5000_recall, T_5000_TP, T_5000_TN, T_5000_FP, T_5000_FN))

    
    return MARS_f1, MARS_precision, MARS_recall, MARS_TP, MARS_TN, MARS_FP, MARS_FN, \
        SKETCH_f1, SKETCH_precision, SKETCH_recall, SKETCH_TP, SKETCH_TN, SKETCH_FP, SKETCH_FN,\
        T_100_f1, T_100_precision, T_100_recall, T_100_TP, T_100_TN, T_100_FP, T_100_FN,\
        T_1000_f1, T_1000_precision, T_1000_recall, T_1000_TP, T_1000_TN, T_1000_FP, T_1000_FN,\
        T_500_f1, T_500_precision, T_500_recall, T_500_TP, T_500_TN, T_500_FP, T_500_FN,\
        T_5000_f1, T_5000_precision, T_5000_recall, T_5000_TP, T_5000_TN, T_5000_FP, T_5000_FN