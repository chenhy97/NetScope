# coding: utf8

import argparse
import json
import pandas as pd
import os
import sys
import numpy as np
from matplotlib import pyplot as plt
from ast import literal_eval
from multiprocessing import Pool
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ANALYSIS_DIR  = Path(__file__).resolve().parent
sys.path.append(ANALYSIS_DIR)
os.chdir(ROOT_DIR)
from reservoir import Reservoir
from algrithm import diff
from utils import export_FSP, detect_abnormal_timespan, PPS
from load import Loader
from spmf import Spmf

DEPTH_STD_THRESHOLD = 2
PPS_THRESHOLD = 2
ECMP_THRESHOLD = 0.65  # 100%
SIGMA_NUM = 10

DEPTH_STD_THRESHOLD = 2
PPS_THRESHOLD = 1.5
ECMP_THRESHOLD = 0.8  # 100%
SIGMA_NUM = 3


def get_sw_src_dst(path):
    path = path.rstrip(',').split(',')
    return f"{path[0]}-{path[-1]}"


def find_fork(paths):
    paths = sorted(paths)
    fork = -1

    if len(paths) > 1:
        fork = -1
        for i in range(len(paths[0])):
            hops = [p[i] for p in paths]
            if len(set(hops)) > 1:
                fork = i - 1
                break

    return fork


def process_reservoir(flow_df):
    '''每个流各自一个 Reservoir'''
    sigma_num = SIGMA_NUM
    zoom = 1e3
    flow_adr = Reservoir(volumn=len(flow_df) / 10, sigma_num=sigma_num)
    for i, row in flow_df.iterrows():
        flow_df.loc[i, 'lier'] = flow_adr.feed(row['latency'] / zoom)

    return flow_df


def localize_drop(digests, topo):
    if 'src_epoch_gap' not in digests.columns:
        return pd.DataFrame()
    drop_df = digests[(digests.src_epoch_gap > 0)
                      & (digests.src_epoch_gap < 15)]

    # drop_weight_df
    drop_list = []
    for _, row in drop_df.iterrows():
        d = row.src_epoch_gap
        if row.flow_drop < row.flow_count:  # sink < source: this path drop
            drop_list.append(dict(whole_path=row.whole_path, weight=d))
        else:  # sink > source: other path drop
            paths = topo.get_shortest_paths_between_nodes(row.src, row.dst)
            w = d / max(1, len(paths) - 1)
            for path in paths:
                whole_path = ",".join(path)
                if whole_path == row.whole_path:
                    continue
                drop_list.append(dict(whole_path=whole_path, weight=w))
    drop_weight_df = pd.DataFrame(drop_list)
    if len(drop_weight_df) < 2:
        print(f"drop_weight_df: {len(drop_weight_df)}")
        return pd.DataFrame()
    drop_weight_df['path_str'] = drop_weight_df.whole_path.apply(
        lambda x: "".join([f"{s}," for s in x.split(',')[1:-1]]))

    # drop_patterns
    drop_patterns = []
    for drop_path in drop_weight_df.path_str.unique():
        drop_path = [h.lstrip('s') for h in drop_path.strip(',').split(',')]
        for i in range(len(drop_path) - 1):
            drop_patterns.append(drop_path[i] + ',' + drop_path[i + 1])
            # drop_patterns.append([[drop_path[i]], [drop_path[i+1]]])
    drop_patterns = [[[p.split(',')[0]], [p.split(',')[1]]]
                     for p in set(drop_patterns)]

    suspect_drop = digests[(digests.timestamp >= drop_df.timestamp.min())
                           & (digests.timestamp <= drop_df.timestamp.max()) &
                           (digests.flow_count - digests.flow_drop == 0)]
    if len(suspect_drop) == 0:
        print(f"suspect_drop: {len(suspect_drop)}")
        return pd.DataFrame()

    drop_diff_df = diff(drop_patterns,
                        drop_weight_df,
                        suspect_drop,
                        th_supp=0,
                        th_rr=0,
                        count='weight')
    drop_diff_df['rank'] = drop_diff_df['score'].rank(method='dense',
                                                      ascending=False)
    drop_diff_df = drop_diff_df.rename(columns={
        'score': 'general_score',
        'pattern': 'culprit',
        'support': 'suggestion'
    })
    drop_diff_df['kind'] = 'drop_link'
    drop_diff_df = drop_diff_df.drop(['len'], axis=1)
    return drop_diff_df


def analysis_ecmp_imbalance(rca_, df, topo, timespan, ECMP_THRESHOLD):
    cf = rca_['culprit'].strip(',').split(',')  # culprit flow
    cut_len = int((timespan[1] - timespan[0]) / 1e7)
    cut_len = 3
    backup_paths = sorted([
        p for p in topo.get_shortest_paths_between_nodes(cf[0], cf[-1])
        if 's0' not in p
    ])
    if len(backup_paths) == 1:
        return rca_

    fork_idx = find_fork(backup_paths)
    timespan_df = df[(df.timestamp >= timespan[0])
                     & (df.timestamp <= timespan[1])].copy(deep=True)
    if len(timespan_df) == 0:
        return rca_
    timespan_df['epoch'] = pd.cut(timespan_df['receive_t'],
                                  cut_len,
                                  labels=list(range(cut_len)))

    flow_size = np.zeros(shape=(len(backup_paths), cut_len))
    for epoch, sdf in timespan_df.groupby(['epoch']):
        for pi, bp in enumerate(backup_paths):
            ssdf = sdf[sdf.path_str == ",".join(bp) + ","]
            flow_size[pi, epoch] = ssdf.path_pkt_size.sum()
    flow_size = flow_size[:, flow_size.sum(axis=0) != 0]  # 去掉和为0的，避免处以0报错
    flow_ratio = flow_size / flow_size.sum(axis=0)
    flow_ratio = flow_ratio[:, (flow_ratio != 1).all(axis=0)]
    if (flow_ratio > ECMP_THRESHOLD).any():
        rca_.update(
            dict(culprit=backup_paths[0][fork_idx],
                 kind='ecmp imbalance',
                 value=flow_ratio.max(),
                 test=cf))
        rca_["comment"] = rca_.get('comment', "") + str(backup_paths)
    return rca_


def diagnosis(sw_df,
              R_df,
              flow_dfs,
              df,
              topo,
              DEPTH_STD_THRESHOLD,
              PPS_THRESHOLD,
              ECMP_THRESHOLD,
              printf=print):

    rca_data = []
    for _, sw_row in sw_df.iterrows():
        # switch or link
        culprit_pos = sw_row.pattern
        printf(f"\nculprit postion is at {culprit_pos}")
        # 按频数序获得经过 culprit_pos 的异常 flow，频数越高的 flow 越可疑
        # `value_counts()` return descending order defaultly
        culprit_flows_series = R_df[R_df['path_str'].str.contains(
            culprit_pos)].value_counts('path_str')
        flow_total_counts = culprit_flows_series.values.sum()

        for culprit_flow, count in culprit_flows_series.items():
            # 异常流（嫌疑流/受害流）：流经故障位置(culprit_pos)次数最多的流
            # printf('culprit flow:', culprit_flow)
            culprit_flow_df = df[df.path_str == culprit_flow].copy(deep=True)
            timespan = detect_abnormal_timespan(culprit_flow_df)
            # timespan = (min(digests.timestamp), max(digests.timestamp))
            printf(timespan)
            if len(timespan) == 0:  # 没有检测出异常区间
                printf("fail to find abnormal timespan")
                continue

            qdepthes = culprit_flow_df['qdepth'].tolist()  # 全局的队列深度列表
            culprit_flow_dep_std = np.std(qdepthes)
            printf(
                f"abnormal flow ({culprit_flow}) qdepth std: {culprit_flow_dep_std:.2f}"
            )

            general_score = sw_row.score * (count / flow_total_counts)

            rca_ = {
                'general_score': general_score,
                'abnormal_pos': culprit_pos,
                'abnormal_flow': culprit_flow,
                'len': sw_row.len
            }

            if culprit_flow_dep_std < DEPTH_STD_THRESHOLD and 'kind' not in rca_:
                # 没有发生队列徒增
                rca_.update(
                    dict(kind="switch link",
                         culprit=culprit_pos,
                         value=culprit_flow_dep_std))

            # 时间窗口截取
            pps_rate_dict = {
                p: PPS(flow_dfs[p], timespan)
                for p in flow_dfs.keys()
            }
            # pps_rate_dict = {flow: PPS(sdf, timespan) for flow, sdf in df.groupby(['flow'])}

            cul_pps = pps_rate_dict[culprit_flow]
            printf(
                f"abnormal flow pps: {cul_pps.normal:.2f}->{cul_pps.abnormal:.2f} ({'+' if cul_pps.rate>0 else ''}{cul_pps.rate*100:.1f}%)"
            )
            # print(cul_pps.rate)

            rca_.update(dict(pps=cul_pps.rate))
            if cul_pps.rate > PPS_THRESHOLD and 'kind' not in rca_:
                rca_.update(
                    dict(kind='flow', culprit=culprit_flow,
                         value=cul_pps.rate))
                # print(f"root cause: flow ({culprit_flow})")

            pps_rate_sorted = sorted(pps_rate_dict.items(),
                                     key=lambda x: x[1].rate,
                                     reverse=True)
            printf(
                f"1st diff pps ({pps_rate_sorted[0][0]}): {pps_rate_sorted[0][1].abnormal:.1f} ({pps_rate_sorted[0][1].rate*100:.1f}%)"
            )
            # if pps_rate_sorted[0][1].rate == np.inf:
            #     print(f"2nd abnormal pps: {pps_rate_sorted[1][1].abnormal:.1f}")
            if pps_rate_sorted[0][
                    1].rate > PPS_THRESHOLD and 'kind' not in rca_:
                printf('flow', pps_rate_sorted[0][0])
                rca_.update(
                    dict(kind='flow',
                         culprit=pps_rate_sorted[0][0],
                         comment="first;",
                         value=pps_rate_sorted[0][1].rate))

            if 'kind' not in rca_:
                rca_.update(
                    dict(kind='port queue rate',
                         culprit=culprit_pos,
                         comment=cul_pps.rate))

            if rca_['kind'] == "flow":
                rca_ = analysis_ecmp_imbalance(rca_, df, topo, timespan,
                                               ECMP_THRESHOLD)

            rca_data.append(rca_)

    rca_df = (pd.DataFrame(rca_data).sort_values('len').sort_values(
        'general_score', ascending=False, ignore_index=True))

    rca_merge = []
    for culprit in rca_df['culprit'].unique():
        # print(culprit)
        cul_df = rca_df[rca_df['culprit'] == culprit]
        for kind in cul_df['kind'].unique():
            kind_df = cul_df[cul_df['kind'] == kind]

            # general_score=kind_df['general_score'].to_numpy().sum()
            # print(general_score)
            if kind == "flow":
                general_score = max(kind_df['general_score'])  # TODO:
                # general_score=sum(kind_df['general_score'])
            else:
                general_score = sum(kind_df['general_score'])
            rca_temp = dict(general_score=general_score,
                            abnormal_pos=kind_df['abnormal_pos'].unique(),
                            abnormal_flow=kind_df['abnormal_flow'].unique(),
                            culprit=culprit,
                            kind=kind)

            if culprit.count(',') == 1:  # single switch
                suggestion_df = rca_df[
                    (rca_df['culprit'].str.contains(culprit))
                    & (rca_df['len'] > 1)]
                if general_score == np.inf:
                    suggestion_df = suggestion_df[
                        suggestion_df['general_score'].rank(
                            method='dense', ascending=False) == 1]
                else:
                    suggestion_df = suggestion_df[
                        suggestion_df['general_score'] == general_score]
                rca_temp['suggestion'] = suggestion_df['culprit'].unique()

            rca_merge.append(rca_temp)
        # break

    rca_merge_df = pd.DataFrame(rca_merge).sort_values(
        'general_score', ascending=False,
        ignore_index=True)  # .reset_index(drop=True)

    # merge path if they belong to same flow
    # flow def: same src switch and same dst switch
    flow_rca_df = rca_merge_df[rca_merge_df.kind == 'flow'].copy(deep=True)
    flow_rca = []

    def get_sw_src_dst(path):
        path = path.rstrip(',').split(',')
        return f"{path[0]}-{path[-1]}"

    flow_rca_df['suggestion'] = flow_rca_df.culprit.apply(get_sw_src_dst)
    for flow_sd in flow_rca_df.suggestion.unique():
        flow_df = flow_rca_df[flow_rca_df.suggestion == flow_sd]
        flow_rca.append(
            dict(
                general_score=sum(flow_df.general_score),
                abnormal_pos=flow_df.abnormal_pos.tolist(),
                abnormal_flow=flow_df.culprit.tolist(),
                culprit=flow_sd,
                kind='flow',
            ))
    rca_merge_df = rca_merge_df.drop(flow_rca_df.index)
    rca_merge_df = rca_merge_df.append(pd.DataFrame(flow_rca))
    rca_merge_df = rca_merge_df.sort_values('general_score',
                                            ascending=False,
                                            ignore_index=True)

    rca_merge_df['rank'] = rca_merge_df['general_score'].rank(
        method='dense', ascending=False).astype(int)
    rca_merge_df['rank'] = rca_merge_df['rank'].astype(int)

    return rca_merge_df


def replay(ADR_df):
    '''
    estimate by path count
    通过 path count 把聚合数据近似出单体数据
    '''
    estimate_df = ADR_df.copy(deep=True)
    new_rows = []
    for global_path_id, path_df in ADR_df.groupby(['global_path_id']):
        timestamp_diff = path_df.timestamp.diff()
        for i, row in path_df.iterrows():
            if pd.isna(timestamp_diff[i]):
                continue
            count = int(row['path_count'])
            timestamps = np.linspace(row.timestamp - timestamp_diff[i],
                                     row.timestamp,
                                     count + 1)[1:-1]  # 头尾数据已经存在，不需要再新增

            if count == 0:
                continue

            gause_rates = np.random.normal(1, 0.1, count - 1)
            for k in range(count - 1):
                new_row = row.copy(deep=True)
                new_row.timestamp = int(timestamps[k])
                new_row.latency *= gause_rates[k]
                new_rows.append(new_row)
                # estimate_df = estimate_df.append(new_row)
    estimate_df = pd.concat([estimate_df, pd.DataFrame(new_rows)])
    estimate_df = estimate_df.sort_values('timestamp').reset_index()
    return estimate_df


def analysis(data_path=None, log=True, verbose=False):

    def printf(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    loader = Loader(data_path)
    topo = loader.get_topo()
    registers = loader.load_registers()

    estimate_df = replay(registers)

    paths = sorted(estimate_df['path_str'].unique())
    flow_dfs = {}
    for i, path in enumerate(paths):
        flow_dfs[path] = (estimate_df[estimate_df['path_str'] == path].copy(
            deep=True).reset_index(drop=True))

    # ADR for each flow
    with Pool(len(paths)) as p:
        map_dfs = p.map(process_reservoir, flow_dfs.values())
    map_df = pd.concat(map_dfs)

    # cut off the unkonw part
    unknow_max_t = np.max(map_df[map_df['lier'] == 'unknow']['timestamp'])
    if not np.isnan(unknow_max_t):
        map_df = map_df[map_df['timestamp'] > np.max(
            map_df[map_df['lier'] ==
                   'unknow']['timestamp'])]  # cut off the beginnning of exp

    # 取回digest部分
    df = map_df[pd.isna(map_df.flow_drop) == False].copy(deep=True)

    R_df = df[df['lier'] == 'out']
    S_df = df[df['lier'] == 'in']

    # PrefixSpan
    spmf_name = 'alg_analysis'
    spmf_input_fn = f'spmf/{spmf_name}_input'
    export_FSP(R_df, spmf_input_fn)
    min_support = 0  # 10/len(R_df)
    spmf = Spmf(
        "PrefixSpan",
        arguments=[min_support, 2],  # max pattern len = 2
        input_filename=f"./build/{spmf_input_fn}.txt",
        output_filename=f"./build/spmf/{spmf_name}_output.txt",
        spmf_bin_location_dir="./analysis")
    spmf.run()

    spmf_df = spmf.to_pandas_dataframe()
    frequentPatterns = spmf_df['pattern'].to_list()

    diff_df = diff(frequentPatterns, R_df, S_df, th_supp=0., th_rr=1)
    diff_df_raw = diff_df.copy()

    # merge same support item
    for dup_sup in diff_df[diff_df.duplicated('support')]['support'].unique():
        longest = []
        dup_df = diff_df[diff_df['support'] == dup_sup].sort_values('len')
        longest = dup_df['pattern'].to_list()[-1]
        for index, row in dup_df[:-1].iterrows():
            if row['pattern'] in longest:
                diff_df.drop(index, inplace=True)

    sw_df = diff_df_raw[diff_df_raw['len'] <= 2]
    rca_df = diagnosis(sw_df,
                       R_df,
                       flow_dfs,
                       df,
                       topo,
                       DEPTH_STD_THRESHOLD=DEPTH_STD_THRESHOLD,
                       PPS_THRESHOLD=PPS_THRESHOLD,
                       ECMP_THRESHOLD=ECMP_THRESHOLD,
                       printf=printf)

    drop_rca_df = localize_drop(registers, topo)
    rca_total_df = pd.concat([rca_df, drop_rca_df])
    rca_total_df['rank'] = rca_total_df['rank'].astype(int)

    if log == True:
        rca_total_df.to_csv(loader.log_dir / 'rca.csv', index=False)
        rca_total_df.to_csv(ROOT_DIR / 'build/rca.csv', index=False)

        print(rca_total_df.head(5))

    return rca_total_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, required=False, default=None)
    parser.add_argument('--log', type=bool, required=False, default=True)
    parser.add_argument('--verbose', type=bool, required=False, default=False)
    args = parser.parse_args()

    if args.data_path == "input":
        args.data_path = input("data_path: ")

    analysis(args.data_path, log=args.log, verbose=args.verbose)
