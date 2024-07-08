from scapy.all import Packet, IPOption
from scapy.all import PacketListField, ShortField, IntField, LongField, BitField, FieldListField, FieldLenField
from scapy.layers.inet import _IPOption_HDR

class INT_Header(Packet):
    name = "int_header"
    fields_desc = [
        BitField("prev_index_sketch0", 0, 32),
        BitField("prev_index_sketch1", 0, 32),
        BitField("prev_index_sketch2", 0, 32),
        BitField("latency", 0, 48),
        BitField("lambda_value0", 0, 48),
        BitField("lambda_value1", 0, 48),
        BitField("lambda_value2", 0, 48),

        BitField("quantile_value_sketch0", 0, 48),
        BitField("quantile_value_sketch1", 0, 48),
        BitField("quantile_value_sketch2", 0, 48),
        BitField("max_gap_value_sketch0", 0, 48),
        BitField("min_gap_value_sketch0", 0, 48),
        BitField("c_minus_value_sketch0", 0, 16),
        BitField("c_plus_value_sketch0", 0, 16),
        BitField("count_sketch0", 0, 16),
        BitField("count_sketch1", 0, 16),
        BitField("count_sketch2", 0, 16),
        BitField("count_sketch", 0, 16),
        BitField("lat_ts_value_sketch0", 0, 48),
        BitField("lat_ts_value_sketch1", 0, 48),
        BitField("lat_ts_value_sketch2", 0, 48),

        BitField("max_value_sketch0", 0, 48),
        BitField("max_value_sketch1", 0, 48),
        BitField("max_value_sketch2", 0, 48),
        BitField("min_value_sketch0", 0, 48),
        BitField("min_value_sketch1", 0, 48),
        BitField("min_value_sketch2", 0, 48),
        # BitField("temp_ingr_ts", 0, 48),
        # BitField("temp_egr_ts", 0, 48),
    ]