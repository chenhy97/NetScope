import pandas as pd
import numpy as np
from collections import defaultdict


EPOCH_SHIFT = 16
IN_DELAY = 20
PN_DELAY = 110
EN_DELAY = 60

EPOCH_LENGTH = 2**16  # microseconds
LBW = 100  # Mbps
Q_RATE = 9000  # packets/second (default: 3072) 8400 6300
Q_DEPTH_FRAC = 8
CTH_DEPTH_FRAC = 8  # 4 bw, 8 burst

# 【配置】队列总长度
Q_DEPTH = int(Q_RATE/Q_DEPTH_FRAC)  # packets (default: 128) Q_RATE/20
# packets (1/4 of queue capacity, default: 32) Q_DEPTH/4
CTH_DEPTH = int(Q_DEPTH/CTH_DEPTH_FRAC)
# microseconds 10000 (default: 10000) SLA DEPENDENT
CTH_TIMEDELTA = int((1000000/Q_DEPTH_FRAC)/CTH_DEPTH_FRAC)

STH_BITRATE = int((LBW*1e6*0.5/8)/(1e6/EPOCH_LENGTH))

# df['epoch'] = df.timestamp.apply(lambda x: x >> EPOCH_SHIFT)


def IntSight(DF):
    DF = DF.sort_values('timestamp', ignore_index=True)
    DF['flow'] = DF['src'] + '-' + DF['dst']

    def ddi(): return defaultdict(lambda: defaultdict(
        lambda: defaultdict(int)))  # dict dict int
    def dd0(): return defaultdict(lambda: defaultdict(
        lambda: defaultdict(lambda: np.array([0]*48))))  # dict dict zero
    # sw - flow - epoch
    i_pkts = ddi()
    i_bytes = ddi()

    e_contention_points = dd0()
    e_suspicion_points = dd0()
    e_high_delays = ddi()
    e_ingress_packets = ddi()
    e_egress_packets = ddi()
    e_bytes = ddi()

    df = DF.copy(deep=True)
    timestamp_base = min(df.timestamp)

    def cal_epoch(t): return (t - timestamp_base) >> EPOCH_SHIFT

    reports = []
    e_epochs = set()
    for i, row in df.iterrows():
        ########################
        # # Ingress
        ########################
        i_sw = row.debug[0]['sw_id']
        i_epoch = cal_epoch(row.debug[0]['timestamp'])
        i_pkts[i_sw][row.flow][i_epoch] += 1
        i_bytes[i_sw][row.flow][i_epoch] += row.debug[0]['packet_length']

        # ingress_packets = i_pkts[i_sw][row.flow][i_epoch]
        # ingress_bytes = i_bytes[i_sw][row.flow][i_epoch]

        ########################
        # # Egress
        ########################
        # INGRESS NODE PROCESSING (PART 2)
        e2e_delay = IN_DELAY
        contention_points = np.array([0]*48)
        suspicion_points = np.array([0]*48)

        # PROCESSING ON ALL NODES
        for path_length, hop in enumerate(row.debug):
            # INCREMENT FIELD: END-TO-END DELAY
            e2e_delay += PN_DELAY + hop['deq_timedelta']
            # CONTENTION?
            if hop['deq_timedelta'] >= CTH_TIMEDELTA or hop['enq_qdepth'] >= CTH_DEPTH:
                # MARK FIELD: CONTENTION POINTS
                contention_points[path_length] = 1
            # SUSPICION?
            if i_bytes[i_sw][row.flow][i_epoch] >= STH_BITRATE:
                suspicion_points[path_length] = 1
        df.loc[i, 'telemetry'] = [dict(
            contention_points=contention_points,
            suspicion_points=suspicion_points,
            e2e_delay=e2e_delay,
            i_epoch=i_epoch,
            i_packets=i_pkts[i_sw][row.flow][i_epoch],
            i_bytes=i_bytes[i_sw][row.flow][i_epoch],
            i_sw=i_sw,
        )]
        df.loc[i, 'e_timestamp'] = row.debug[-1]['timestamp']

    for i, row in df.sort_values('e_timestamp').iterrows():
        # EGRESS NODE PROCESSING
        i_sw = row.telemetry['i_sw']
        i_epoch = row.telemetry['i_epoch']

        e_epoch = cal_epoch(row.debug[-1]['timestamp'])
        e_sw = row.debug[-1]['sw_id']
        e_epochs.add(e_epoch)
        e_contention_points[e_sw][row.flow][e_epoch] += row.telemetry['contention_points']
        e_suspicion_points[e_sw][row.flow][e_epoch] += row.telemetry['suspicion_points']
        e_bytes[e_sw][row.flow][e_epoch] += row.debug[-1]['packet_length']

        if row.telemetry['e2e_delay'] >= 20000:
            e_high_e2e_delay = 1
        else:
            e_high_e2e_delay = 0
        if i_epoch != e_epoch:
            e_high_delays[e_sw][row.flow][e_epoch] = e_high_e2e_delay
        elif e_high_e2e_delay == 1:
            e_high_delays[e_sw][row.flow][e_epoch] += 1

        # if row.telemetry['e2e_delay'] >= 20000 and i_epoch != e_epoch:
        #     print("row.telemetry['e2e_delay'] >= 20000")
        #     print(e_high_delays[e_sw][row.flow][e_epoch], i_epoch, e_epoch)

        e_drops = e_ingress_packets[e_sw][row.flow][e_epoch] - \
            e_egress_packets[e_sw][row.flow][e_epoch]
        e_ingress_packets[e_sw][row.flow][e_epoch] = i_pkts[i_sw][row.flow][i_epoch]
        e_egress_packets[e_sw][row.flow][e_epoch] += 1

        # Clone
        if e_epoch != i_epoch and len(e_epochs) > 1:
            # last_e_epoch = sorted(e_epochs)[-2]  # 上一个epoch
            last_e_epoch = e_epoch  # debug
            path_len = row.debug
            r_tmp = dict(
                i_epoch=i_epoch,
                e_epoch=e_epoch,
                flow=row.flow,
                path_id=row.path_id,
                contention_points=''.join(
                    map(str, e_contention_points[e_sw][row.flow][last_e_epoch]))[:len(path_len)],
                suspicion_points=''.join(
                    map(str, e_suspicion_points[e_sw][row.flow][last_e_epoch]))[:len(path_len)],
                high_delays=e_high_delays[e_sw][row.flow][last_e_epoch],
                delay=row.telemetry['e2e_delay'],
                drops=e_drops,
                i_bytes=row.telemetry['i_bytes'],
                e_bytes=e_bytes[e_sw][row.flow][e_epoch],
                e_pkts=e_egress_packets[e_sw][row.flow][e_epoch],
            )
            r_tmp.update(dict(
                whole_path=row.whole_path
            ))
            reports.append(r_tmp)

    report = pd.DataFrame(reports)
    for points in ['contention_points', 'suspicion_points']:
        report[points] = report[points].str.replace('0', '-')
    return report
