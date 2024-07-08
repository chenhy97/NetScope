/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

const bit<16> TYPE_IPV4 = 0x800;

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;


header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header int_header_t {
    bit<32>             prev_index_sketch0;
    bit<32>             prev_index_sketch1;
    bit<32>             prev_index_sketch2;
    bit<48> latency;
    bit<48> lambda0;
    bit<48> lambda1;
    bit<48> lambda2;

    bit<48> quantile_value_sketch0;
    bit<48> quantile_value_sketch1;
    bit<48> quantile_value_sketch2;

    bit<48> max_gap_value_sketch0;
    bit<48> min_gap_value_sketch0;
    bit<16> c_minus_value_sketch0;
    bit<16> c_plus_value_sketch0;
    bit<16> count_sketch0;
    bit<16> count_sketch1;
    bit<16> count_sketch2;
    bit<16> count_sketch;
    bit<48>             lat_ts_value_sketch0;
    bit<48>             lat_ts_value_sketch1;
    bit<48>             lat_ts_value_sketch2;
    bit<48>             max_value_sketch0;
    bit<48>             max_value_sketch1;
    bit<48>             max_value_sketch2;
    bit<48>             min_value_sketch0;
    bit<48>             min_value_sketch1;
    bit<48>             min_value_sketch2;
    // bit<48> temp_ingr_ts;
    // bit<48> temp_egr_ts;
}


header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<6>    dscp;
    bit<2>    ecn;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header tcp_t{
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<1>  cwr;
    bit<1>  ece;
    bit<1>  urg;
    bit<1>  ack;
    bit<1>  psh;
    bit<1>  rst;
    bit<1>  syn;
    bit<1>  fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

struct metadata {
    bit<32>             prev_index_sketch0;
    bit<32>             prev_index_sketch1;
    bit<32>             prev_index_sketch2;
    bit<32>             debug_index_sketch0;
    bit<32>             debug_index_sketch1;
    bit<32>             debug_index_sketch2;


    bit<48>             lat_ts_value_sketch0;
    bit<48>             lat_ts_value_sketch1;
    bit<48>             lat_ts_value_sketch2;

    bit<16>             count_value_sketch0;
    bit<16>             count_value_sketch1;
    bit<16>             count_value_sketch2;
    bit<16>             count_value_sketch;
    bit<16>             percentile_result;
    // bit<8>              chosen_idx;

    bit<16>             c_plus_value_sketch0;
    bit<16>             c_plus_value_sketch1;
    bit<16>             c_plus_value_sketch2;
    bit<16>             c_minus_value_sketch0;
    bit<16>             c_minus_value_sketch1;
    bit<16>             c_minus_value_sketch2;


    bit<48>             quantile_value_sketch0;
    bit<48>             quantile_value_sketch1;
    bit<48>             quantile_value_sketch2;
    bit<48>             temp_ingr_ts;
    bit<48>             temp_egr_ts;

    bit<48>             max_gap_value_sketch0;
    bit<48>             max_gap_value_sketch1;
    bit<48>             max_gap_value_sketch2;
    bit<48>             min_gap_value_sketch0;
    bit<48>             min_gap_value_sketch1;
    bit<48>             min_gap_value_sketch2;
    bit<48>             lambda_value0;
    bit<48>             lambda_value1;
    bit<48>             lambda_value2;


    bit<48>             latency;
    bit<48>             tmp_max_gap_value0;
    bit<48>             tmp_max_gap_value1;
    bit<48>             tmp_max_gap_value2;
    bit<48>             max_value_sketch0;
    bit<48>             max_value_sketch1;
    bit<48>             max_value_sketch2;
    bit<48>             min_value_sketch0;
    bit<48>             min_value_sketch1;
    bit<48>             min_value_sketch2;

}
header lat_header_t {
    bit<48>             latency;
}

struct headers {
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    tcp_t        tcp;
    lat_header_t   lat;
    int_header_t   int_hdr;
}

