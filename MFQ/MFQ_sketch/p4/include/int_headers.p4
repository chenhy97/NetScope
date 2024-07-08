#ifndef __CUSTOM_HEADERS__
#define __CUSTOM_HEADERS__

#ifndef __INT_HEADERS__
#define __INT_HEADERS__

#include "headers.p4"

const bit<5>  IPV4_OPTION_INT = 31;
const bit<5>  IPV4_OPTION_INT_REPORT = 29;
const bit<5>  IPV4_OPTION_LATENCY = 28;
const bit<5>  IPV4_OPTION_NOTICE = 27;

#define IPV4_OPTION_HS 4 // bytes
// option must be 32x bits, i.e. 4x Bytes.
header ipv4_option_t {
    bit<1>  copyFlag;
    bit<2>  optClass;
    bit<5>  option;
    bit<8>  optionLength;
    // 16 bits
    count_t src_count; // TODO: What if exceed?
    bit<3>  path_id;
    bool    abnormal_detected;
}

// ethernet (48+48+16 = 112 bits)          = 14 bytes
#define ETH_HS 14
// ipv4     (160 bits) + ipv4_opt(32 bits) = 24 bytes
// udp      (4*16 = 64 bits)               =  8 bytes
#define UDP_HS 8 
#define UDP_LEN (ETH_HS + (20 + IPV4_OPTION_HS) + UDP_HS)


#define INT_SHIM_HS 15  // bytes
header int_shim_header_t { // 72b = 9B
    bit<48> latency;
    bit<48> src_timestamp; // source node ingress timestamp
    qdepth_sum_t qdepth_sum; // TODO: What if exceed?
    bit<4> src_epoch;
    // bit<4> src_epoch_this;
    // bit<4> src_epoch_last;
}

// #define INT_REPORT_SHIM_HS 1
// header int_report_shim_t {
//     bit<8> count;
// }

#define INT_REPORT_HS 29 // 216b
header int_report_t {
    // bit<16>      flow_id;
    bit<8>       index;
    bit<32>      src_ip;
    bit<32>      dst_ip;
    bit<48>      epoch_ingress_timestamp;
    bit<48>      latency;
    qdepth_sum_t qdepth_sum; // 20b
    bit<16>      path_pkt_size;
    count_t      path_count;
    count_t      flow_count; // 12b
    count_t      flow_drop;
    bit<3>       path_id;
    bit<1>       resv;
    bit<4>       src_epoch_gap;
}

#define Latency_SHIM_HS 14
header latency_report_shim_t {
    bit<32> src_ip;
    bit<32> dst_ip;
    bit<16> src_port;
    bit<16> dst_port;
    bit<8>  protocol;
    bit<7>  flow_id;
    bit<1>  conflict;
}

#define Latency_HS 6
header latency_report_t {
    bit<48> latency;
}

header latency_recir_t {
    bit<32> src_ip;
    bit<32> dst_ip;
    bit<16> src_port;
    bit<16> dst_port;
    bit<8>  protocol;
    bit<7>  flow_id;
    bit<1>  conflict;
}


#define DEBUG_SHIM_HS 1
header debug_shim_t {
    bit<8> count;
}

#define DEBUG_HS 28
header debug_t { 
    switchID_t  swid; // 16 bits = 2 Byte
    bit<9>  ingress_port;
    bit<9>  egress_port;
    // bit<9>  meta_ingress_port;
    // bit<9>  meta_egress_port;
    // bit<16> qdepth;
    // bit<3>  L_idx;
    // bit<3>  L_idx2;
    // bit<1>  flag1;
    // bit<1>  flag2;
    // bit<1>  flag3;
    // bit<1>  flag4;
    // bit<32> src_ip0;
    // bit<32> src_ip1;
    // bit<48> tstamp;
    // bit<48> tstamp2;
    bit<5> state_i;
    bit<6> state;
    // bit<8> option;
    // bit<16> resv2;
    // bit<6> resv3;
    // bit<12> resv;

    // evaluation
    bit<48> timestamp;
    bit<16> qdepth;
    bit<32> packet_length;
    bit<32> enq_timestamp;
    bit<32> deq_timedelta;
    bit<19> enq_qdepth;
    // bit<5> resv;
}



struct headers {
    ethernet_t             ethernet;
    vlan_tag_h             vlan;
    
    ipv4_t                 ipv4;
    ipv4_option_t          ipv4_option;

    udp_t                  udp;
    tcp_h                  tcp;

    int_shim_header_t      int_shim;
    
    latency_report_shim_t  latency_shim;
    latency_report_t[10]   latency_data;
    
    // int_report_shim_t      int_report_shim;
    // int_report_t[150]      int_report;
    int_report_t           int_report;

    debug_shim_t           debug_shim;
    debug_t[16]            debug;

    metadata_temp_t             md;
}


#endif // __INT_HEADERS__
#endif // __CUSTOM_HEADERS__