import json
from multiprocessing import context
import os
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import requests

data_folder = 'host_log'
root_folder = os.path.dirname(os.path.dirname((os.path.abspath(__file__))))


def export_FSP(df, fn="SequentialPattern"):
    content = ""
    for path_str in df['path_str']:
        path = path_str.rstrip(',').split(',')
        content += ' -1 '.join(path).replace("s", "")
        content += " -1 -2\n"
    with open(os.path.join(root_folder, 'build', f'{fn}.txt'), 'w') as f:
        f.write(content)


def continue_idx(arr):
    '''called by detect_abnormal_timespan'''
    count = 0
    effect_index = []
    for i in range(len(arr) - 1):
        if arr[i] + 1 != arr[i + 1]:  # continue end
            if count != 0:
                effect_index[-1][1] = count  # udpate count
                count = 0  # refresh count
            continue
        else:
            if count == 0:
                effect_index.append([arr[i], 1])
            count += 1
            if i == len(arr) - 2:  # the last one
                effect_index[-1][1] = count  # udpate count
    return sorted(effect_index, key=lambda x: x[1], reverse=True)


def detect_abnormal_timespan(culprit_flow_df):
    '''return begin time and end time of abnormal timespan'''
    if len(culprit_flow_df) < 11:
        return [0, 0]
    smooth = savgol_filter(culprit_flow_df['latency'].to_list(), 11, 1)
    grad = np.gradient(smooth)
    std = np.std(grad)

    over_std = np.where(grad > std / 2)[0]
    below_std = np.where(grad < -std / 2)[0]

    begin_indexs = continue_idx(over_std)
    if not begin_indexs:
        return [0, 0]
    begin_index = begin_indexs[0][0]

    end_indexs = continue_idx(below_std)
    if end_indexs:
        end_index = end_indexs[0]
        end_index = end_index[0] + end_index[1]
    else:
        end_index = max(over_std)

    timestamps = culprit_flow_df['timestamp'].tolist()
    begin_t = timestamps[begin_index]
    end_t = timestamps[end_index]
    return begin_t, end_t


class PPS():

    def __init__(self, df, timespan, pre_offset=10, self_detect=False):
        if self_detect:
            self.timespan = detect_abnormal_timespan(df)
        else:
            self.timespan = timespan
        begin_t, end_t = self.timespan
        self.abnormal = self.cal_pps(df[(df['timestamp'] > begin_t)
                                        & (df['timestamp'] < end_t)])

        normal_df = df[df['timestamp'] < begin_t]
        if len(normal_df) < pre_offset:
            normal_df = df.reset_index(drop=True)[:pre_offset]
        self.normal = self.cal_pps(normal_df)

        # pps changing rate
        if self.normal == 0 and self.abnormal > 0:
            self.rate = np.inf
        else:
            self.rate = np.divide(self.abnormal - self.normal, self.normal)

    def cal_pps(self, df):
        tstamps = df['timestamp'].to_list()
        if len(set(tstamps)) > 2:
            return len(df) / ((max(tstamps) - min(tstamps)) / 1e6)  # pps
        else:
            return 0


def wechat_bot(message):
    api = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=9a41bc20-dd0c-4a26-82d9-0f9d8c00a624'
    headers = {"Content-Type": "text/plain"}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": message,
            "mentioned_list": ["@all"],
            "mentioned_mobile_list": ["@all"],
        }
    }
    r = requests.post(api, headers=headers, json=data)


def ip_int_to_str(x):
    return '.'.join([str(int(x / (256**i) % 256)) for i in range(4)][::-1])


if __name__ == '__main__':
    # import os
    # print(os.getcwd())
    pass
