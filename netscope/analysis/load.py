import re
import json
import os
import sys
import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

import platform

if platform.system() == 'Darwin':
    from .local.graph import load_topo
else:
    from p4utils.utils.helper import load_topo

data_folder = 'host_log'
root_folder = os.path.dirname(os.path.dirname((os.path.abspath(__file__))))
ROOT_DIR = Path(__file__).resolve().parent.parent
if True:
    sys.path.append(str(ROOT_DIR / 'analysis'))
    from topo import host2sw, ip2h
    from utils import ip_int_to_str


def load_json(fn, mode='r'):
    with open(fn, mode) as f:
        content = f.read()
        content = '[' + content.rstrip(',\n') + ']'
        return json.loads(content)


class Loader():

    def __init__(self, log_dir=None):
        if log_dir is None or 'log' in log_dir:
            self.log_dir = ROOT_DIR / 'log/hosts'
            self.topo_path = ROOT_DIR / 'topology.json'  #   'build', 'topo_without_collector.json')
            pathsjson_path = ROOT_DIR / "build/paths.json"
        elif isinstance(log_dir, (str, Path)):
            log_dir = Path(log_dir)
            self.log_dir = log_dir / 'mininet/hosts'
            self.topo_path = log_dir / 'topology.json'  #   'topo_without_collector.json')
            pathsjson_path = log_dir / "paths.json"
        else:
            raise Warning(f"Unknown log_dir type {type(log_dir)}")

        if os.path.exists(pathsjson_path):
            with open(pathsjson_path, "r") as f:
                self.path_ids = json.load(f)

        topo = load_topo(self.topo_path)
        self.host2sw = lambda h: host2sw(topo, h)
        self.ip2h = lambda h: ip2h(topo, h)

    def get_topo(self):
        return load_topo(self.topo_path)

    def tag_df(self, df):
        df['global_path_id'] = df['src'].apply(
            self.host2sw) + "-" + df['dst'].apply(
                self.host2sw) + ":" + df['path_id'].astype(str)
        df['path'] = df['global_path_id'].apply(
            lambda gpid: self.path_ids.get(gpid, defaultdict(list))['path'])
        df['path_str'] = df['path'].apply(
            lambda p: "".join([f"{s}," for s in p]))
        df['whole_path'] = df['src'] + ',' + df['path_str'] + df['dst']
        df['flow'] = df['src'] + '-' + df['dst']
        df['arrive_t'] = df.timestamp + df.latency
        return df

    def load_digest(self):
        digest_fns = [
            fn for fn in os.listdir(self.log_dir)
            if re.match(f"s\d+.json", fn)
        ]

        digests = []
        for fn in digest_fns:
            sw = re.match(r"s\d+", fn).group()
            digest = pd.DataFrame(load_json(self.log_dir / fn))
            digest['sw'] = sw
            digests.append(digest)

        if len(digests) == 0:
            return None

        digests = pd.concat(digests)
        digests = digests.rename(columns={
            'epoch_t': 'timestamp',
            'src_ip': 'src',
            'dst_ip': 'dst'
        })
        digests = self.tag_df(digests)
        return digests

    def load_latency(self):
        latency_reports = load_json(self.log_dir / 'h0-eth0-28.json')
        latencys = []
        for lr in latency_reports:
            shim = lr['latency_shim']
            for i in range(shim['count']):
                if lr['latency'][i] == 0:
                    print("[W] Encouanter 0")
                    print(shim['count'], lr['latency'])
                    continue
                latencys.append(
                    dict(
                        src=self.ip2h(shim['src_ip']),
                        dst=self.ip2h(shim['dst_ip']),
                        latency=lr['latency'][i],
                        receive_t=lr['receive_t'],
                    ))
        latencys = pd.DataFrame(latencys)
        return latencys

    def load_hosts(self, host_fns=None, debug=False):
        if host_fns is None:
            host_fns = [
                fn for fn in os.listdir(self.log_dir)
                if re.match(r"h\d+-eth0-31.json", fn)
            ]

        hosts = []
        for fn in host_fns:
            hosts.append(pd.DataFrame(load_json(self.log_dir / fn)))
        hosts = pd.concat(hosts)
        hosts = hosts.rename(columns={
            'src_timestamp': 'timestamp',
            'src_ip': 'src',
            'dst_ip': 'dst'
        })
        if not debug and 'debug' in hosts.columns:
            hosts = hosts.drop(['debug'], axis=1)
        hosts = self.tag_df(hosts)
        return hosts.sort_values('timestamp')

    def load_registers(self):
        if '/log/' not in str(self.log_dir):
            registers = pd.read_csv(f"{self.log_dir.parent}/reg.csv")
        else:
            registers = pd.read_csv(f"{self.log_dir.parent}/reg.csv")
        registers['src'] = registers['src_ip'].apply(
            lambda ip: self.ip2h(ip_int_to_str(ip)))
        registers['dst'] = registers['dst_ip'].apply(
            lambda ip: self.ip2h(ip_int_to_str(ip)))
        registers['timestamp'] = registers['src_tstamp']
        registers = self.tag_df(registers)
        return registers.sort_values('timestamp')


def load_data(log_names, log_dir='./host_log'):
    # load data
    log_data = {}
    for ln in log_names:
        with open(os.path.join(log_dir, ln + '.log'), 'r') as f:
            content = f.read()
            log_data[ln] = json.loads('[' + content.rstrip(',\n') + ']')
    return log_data


def load_dst_hosts(save=False, log_dir='./host_log'):
    log_names = [
        os.path.splitext(l)[0] for l in os.listdir(log_dir)
        if l.endswith('.log') and "interface" not in l
    ]
    log_names.remove('h0-eth0')
    # print(log_names)

    # load data
    log_data = load_data(log_names, log_dir)

    trace_data = []
    for ln in log_names:
        for trace in log_data[ln]:
            trace_latency = trace[-1]['ingress_tstamp'] + \
                trace[-1]['hop_latency'] - trace[0]['ingress_tstamp']
            path = ["s" + str(hop['switch_id']) for hop in trace]
            trace_data.append({
                'dst':
                ln,
                'timestamp':
                trace[0]['ingress_tstamp'],
                # 'path': path,
                'path_str':
                ','.join(path) + ',',
                # 'path': ','.join(["s"+str(hop['switch_id']) for hop in trace]),
                'latency':
                trace_latency,
                'hop_latency':
                sum([hop['hop_latency'] for hop in trace]),
                # 'latency_norm': trace_latency/len(path),
                'qdepthes': [hop['qdepth'] for hop in trace],
                'detail':
                ','.join([
                    "s{}-eth{}".format(hop['switch_id'], hop['egress_port'])
                    for hop in trace
                ]),
            })

    df = pd.DataFrame(trace_data).sort_values(['timestamp'], ignore_index=True)
    df['timestamp'] = df['timestamp'] - df['timestamp'][0]

    if save:
        # df.to_csv('INT-MD2.csv', index=False)
        df.drop(['dst'], axis=1).to_csv(os.path.join(log_dir, 'INT-MD.csv'),
                                        index=False)
    return df


def load_collector(save=False, log_dir='./host_log'):
    collector_name = 'h0-eth0'
    collector_data = load_data([collector_name], log_dir)[collector_name]
    collector_data = [data[0] for data in collector_data]

    df = pd.DataFrame(collector_data)
    trace_id_list = list(set(df['trace_id']))

    trace_data = {}
    for trace_id in trace_id_list:
        trace_df = df[df['trace_id'] == trace_id].sort_values(
            ['ingress_tstamp'], ascending=True, ignore_index=True)
        trace_list = trace_df.to_dict('records')
        for trace in trace_list:
            trace.pop('trace_id')
        trace_data[trace_id] = trace_list

    log_data = []
    for trace_id, trace in trace_data.items():
        # print(trace_id)
        trace_latency = trace[-1]['ingress_tstamp'] + \
            trace[-1]['hop_latency'] - trace[0]['ingress_tstamp']
        path = ["s" + str(hop['switch_id']) for hop in trace]
        log_data.append({
            # 'dst': ln,
            'timestamp':
            trace[0]['ingress_tstamp'],
            'path':
            path,
            'path_str':
            ','.join(path) + ',',
            'latency':
            trace_latency,
            'qdepthes': [hop['qdepth'] for hop in trace],
            'detail':
            ','.join([
                "s{}-eth{}".format(hop['switch_id'], hop['egress_port'])
                for hop in trace
            ]),
        })

    df = pd.DataFrame(log_data).sort_values(['timestamp'], ignore_index=True)
    if save:
        df.to_csv(os.path.join(data_folder, 'INT-MX.csv'), index=False)

    df['timestamp'] = df['timestamp'] - df['timestamp'][0]

    return df


class Register():

    def __init__(self, log_dir='log/log', REG_L=9):
        self.REG_L = REG_L

        sw_logs = {}
        for sw_fn in os.listdir(log_dir):
            sw = sw_fn.split('.')[0]
            with open(os.path.join(log_dir, sw_fn)) as f:
                sw_logs[sw] = f.read().split('bm_reset_state')[-1]
        self.sw_logs = sw_logs

    def load_by_digest_read(self):
        regex = re.compile(  # r"Primitive buffer_\w+\.read\(meta\.D\.report\.\w+, meta\.recir_index\)\n" + \
            r"\[(?P<time>[\d:\.]+)\] \[bmv2\] \[\w\] \[thread (?P<thread>\d+)\] \[(?P<pid>\d+)\.(?P<sub_pid>\d+)\] \[cxt (?P<cxt>\d+)\] " + \
            r"Read register '\w+\.buffer_(?P<register>(?!index_reg)\w*)' at index (?P<idx>\d+) read value (?P<value>\d+)", re.S)
        int_cols = ['thread', 'idx', 'value', 'pid', 'sub_pid']

        buffers = []
        for sw, log in self.sw_logs.items():
            reg_list = [r.groupdict() for r in regex.finditer(log)]
            if len(reg_list) == 0:
                continue
            regs = pd.DataFrame(reg_list)

            regs[int_cols] = regs[int_cols].astype(int)
            regs.register = regs.register.str.replace('src_tstamp',
                                                      'timestamp')

            for group, df_tmp in regs.groupby(['pid', 'sub_pid']):
                if len(df_tmp) == 1 and df_tmp.value.tolist()[0] == 0:
                    continue
                assert len(
                    df_tmp
                ) == self.REG_L, f"Should be {self.REG_L} but not {len(df_tmp)}"
                assert len(df_tmp.idx.unique()) == 1, f'should be same index'
                buffer = dict(
                    zip(df_tmp.register.tolist(), df_tmp.value.tolist()))
                buffer.update(dict(sw=sw, idx=df_tmp.idx.unique()[0]))
                buffers.append(buffer)

        return pd.DataFrame(buffers).sort_values('timestamp',
                                                 ignore_index=True)

    def load_by_write(self):
        buffers = []
        for sw, log in self.sw_logs.items():
            register = re.findall(
                r"\[([\d:\.]+)\] \[bmv2\] \[\w\] \[thread (\d+)\] \[[\d\.]+\] \[cxt (\d+)\] Wrote register '(\w+)\.buffer_(\w+)' at index (\d+) with value (\d+)",
                log)

            regs = pd.DataFrame(register,
                                columns=[
                                    'time', 'thread', 'ctx', 'pipline',
                                    'register', 'id', 'value'
                                ])
            regs = regs[regs.register != 'index_reg'].reset_index()
            regs[['thread', 'id', 'value']] = regs[['thread', 'id',
                                                    'value']].astype(int)
            regs.register = regs.register.str.replace('src_tstamp',
                                                      'timestamp')

            i = 0
            while i + self.REG_L <= len(regs):
                r_tmp = regs[i:i + self.REG_L]
                if list(regs.loc[i,
                                 ['register', 'value']]) == ['timestamp', 0]:
                    i += 1
                    continue

                assert len(
                    r_tmp.id.unique()) == 1, f'should be same index at {i}'
                index = r_tmp.id.unique()[0]

                buffer = dict(
                    zip(r_tmp.register.tolist(), r_tmp.value.tolist()))
                buffer.update(dict(sw=sw, id=index))
                buffers.append(buffer)
                i += self.REG_L

        return pd.DataFrame(buffers).sort_values('timestamp',
                                                 ignore_index=True)
