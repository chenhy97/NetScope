import json
import os
import pandas as pd
from p4utils.utils.helper import load_topo

root_folder = os.path.dirname(os.path.dirname((os.path.abspath(__file__))))


class Loader():
    def __init__(self, log_dir=None):
        if log_dir is None:
            self.log_dir = './log/hosts'
            self.topo_path = os.path.join(root_folder, 'topology.json')
            # pathsjson_path = os.path.join(root_folder, "build/paths.json")
        else:
            self.log_dir = os.path.join(log_dir, 'mininet/hosts')
            self.topo_path = os.path.join(log_dir, 'topology.json')
            # pathsjson_path = os.path.join(log_dir, "paths.json")

        # with open(pathsjson_path, "r") as f:
        #     self.path_ids = json.load(f)

    def get_topo(self):
        return load_topo(self.topo_path)

    def load_pkt_df(self):
        log_dir = self.log_dir
        if "log" in log_dir:
            data_fn = os.path.join(log_dir, 'h0-eth0-29.json')
        else:
            data_fn = os.path.join(log_dir, 'h0-eth0-29.json')
        with open(data_fn, 'r') as f:
            collector_data = json.loads('['+f.read().rstrip(',\n')+']')
        df = pd.DataFrame(collector_data).sort_values(
            ['src_timestamp'], ignore_index=True)

        df['flow'] = df['src_ip'] + '-' + df['dst_ip']
        self.pkt_df = df
        return df

    def load_sw_df(self):
        df = self.pkt_df
        sw_data = []
        for pkt_id, row in df.iterrows():
            for hop in row.traces:
                hop.update(dict(
                    flow=row.flow,
                    pkt_id=pkt_id,
                ))
                sw_data.append(hop)
        sw_dfs = pd.DataFrame(sw_data).sort_values('timestamp')
        return sw_dfs
