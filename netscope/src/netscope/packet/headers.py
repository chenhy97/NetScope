#!/usr/bin/env python
from scapy.all import Packet, IPOption
from scapy.all import PacketListField, ShortField, IntField, LongField, BitField, FieldListField, FieldLenField
from scapy.layers.inet import _IPOption_HDR

# ========== IPv4 ==========


class IPOption_MRI(IPOption):
    name = "IPv4 Option (INT)"
    option = 0
    fields_desc = [
        _IPOption_HDR,
        BitField("length", 0, 8),
        BitField("src_count", 0, 12),
        BitField("path_id", 0, 3),
        BitField("AD", 0, 1),
    ]


class IPv4_option_value(Packet):
    name = "ipv4_option_value"
    fields_desc = IPOption_MRI.fields_desc[4:]


# ========== INT Telemetry ==========
class INT_shim_header(Packet):
    name = "INT_shim"
    fields_desc = [
        BitField("latency", 0, 48),
        BitField("src_timestamp", 0, 48),
        BitField("qdepth_sum", 0, 20),
        BitField("src_epoch", 0, 4),
    ]


# ========== INT Report ==========
class report_item(Packet):
    name = "INT_report_item"
    fields_desc = [
        # BitField("flow_id", 0, 16),
        BitField("index", 0, 8),
        BitField("src_ip", 0, 32),
        BitField("dst_ip", 0, 32),
        BitField("epoch_t", 0, 48),
        BitField("latency", 0, 48),
        BitField("path_pkt_size", 0, 16),
        BitField("qdepth", 0, 20),
        BitField("path_count", 0, 12),
        BitField("flow_count", 0, 12),
        BitField("flow_drop", 0, 12),
        BitField("resv", 0, 1),
        BitField("path_id", 0, 3),
        BitField("src_epoch_gap", 0, 4),
    ]

    def extract_padding(self, p):
        return "", p


class INT_report_header(Packet):
    name = "INT_report"
    fields_desc = [
        PacketListField(
            "reports",
            [],
            report_item)
    ]

# ========== Latency ==========


class latency_shim_header(Packet):
    name = "latency_shim"
    fields_desc = [
        BitField("src_ip", 0, 32),
        BitField("dst_ip", 0, 32),
        BitField("src_port", 0, 16),
        BitField("dst_port", 0, 16),
        BitField("protocol", 0, 8),
        BitField("flow_id", 0, 7),
        BitField("conflict", 0, 1),
    ]


class latency_item(Packet):
    fields_desc = [
        BitField("latency", 0, 48)
    ]

    def extract_padding(self, p):
        return "", p


class latency_header(Packet):
    name = "latency"
    fields_desc = [
        PacketListField(
            "latency",
            [],
            latency_item)
    ]

# ========== DEBUG Switch Trace ==========


class debug_shim_header(Packet):
    name = "debug_shim"
    fields_desc = [
        BitField("count", 0, 8),
    ]


class debug_item(Packet):
    fields_desc = [
        BitField("sw_id", 0, 16),
        BitField("ig_port", 0, 9),
        BitField("eg_port", 0, 9),
        # BitField("meta_ingress_port", 0, 9),
        # BitField("meta_egress_port", 0, 9),
        # BitField("resv4", 0, 16),
        # BitField("L_idx", 0, 3),
        # BitField("L_idx2", 0, 3),
        # BitField("ingress_tstamp", 0, 48),
        # BitField("hop_latency", 0, 48),
        # BitField("is_sink", 0, 1),
        # BitField("qdepth", 0, 12),
        # BitField("path_id", 0, 16),
        # BitField("flag1", 0, 1),
        # BitField("flag2", 0, 1),
        # BitField("flag3", 0, 1),
        # BitField("flag4", 0, 1),
        #     BitField("src_ip0", 0, 32),
        #     BitField("src_ip1", 0, 32),
        # BitField("tstamp", 0, 48),
        # BitField("tstamp2", 0, 48),
        BitField("state_i", 0, 5),
        BitField("state", 0, 6),
        # BitField("option", 0, 8),
        #     BitField("resv2", 0, 16),
        # BitField("resv", 0, 12),

        BitField("timestamp", 0, 48),
        BitField("qdepth", 0, 16),
        BitField("packet_length", 0, 32),
        BitField("enq_timestamp", 0, 32),
        BitField("deq_timedelta", 0, 32),
        BitField("enq_qdepth", 0, 19),
    ]

    def extract_padding(self, p):
        return "", p


class debug_header(Packet):
    name = "debug"
    fields_desc = [
        PacketListField(
            "hops",
            [],
            debug_item)
    ]


class metadata_header(Packet):
    name = "metadata"
    fields_desc = [
        BitField("load_latency", 0, 1),
        BitField("flow_id_hash_conflict", 0, 1),
        BitField("abnormal_detected", 0, 1),
        BitField("load_telemetry", 0, 1),
        BitField("resv", 0, 4),
    ]
