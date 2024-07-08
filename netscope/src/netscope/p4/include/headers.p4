/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

#ifndef __HEADERS__
#define __HEADERS__

#include "defines.p4"


typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;
typedef bit<16> switchID_t;
typedef bit<12> count_t;
typedef bit<20> qdepth_sum_t;
// typedef bit<48> latency_t;


#define ETHERNET_HS 14 // bytes
header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

#define IPV4_HS 20 // bytes
header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    // bit<8>    diffserv;
    bit<3>    diffserv_priority;
    bit<5>    diffserv_rest;
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


#define UDP_HS 8 // bytes
header udp_t {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> length_;
    bit<16> checksum;
}

#define TCP_HS 20 // bytes
header tcp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> seq_no;
    bit<32> ack_no;
    bit<4> data_offset;
    bit<4> res;
    bit<8> flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgent_ptr;
}


struct int_metadata_t {
    switchID_t swid;   // current switch id
    bool source;
    bool sink;
}

struct path_id_hash_t {
    bit<3> path_hash_control;
    bit<9> ingress_port;
    bit<9> egress_port;
    bit<16> path_id;
}

struct egress_metadata_t {
    // bit<1> multicast;
    bool abnormal_detected;
    ip4Addr_t collector_ip;
}

struct ingress_metadata_t {
    bool     notice_recir;
    bit<4>   epoch;
}

struct clone_latency_t {
    bit<32>  src_ip;
    bit<32>  dst_ip;
}

struct clone_t {
    bool             load_telemetry;
    bool             load_latency;
    bool             flow_id_hash_conflict;
    bool             abnormal_detected;
    clone_latency_t  L;
}

struct latency_t {
    bool     flow_id_hash_conflict;

    // latency list
    bit<3>   idx; // actually bit<3>
    bit<32>  src_ip;
    bit<32>  dst_ip;
}

struct parser_metadata_t {
    count_t latency_count;
    count_t report_count;
    bit<8> debug_count;
}

// struct report_digest_t {
//     // bit<16>      flow_id;
//     // bit<8>       option;
//     bit<8>       index;
//     bit<32>      src_ip;
//     bit<32>      dst_ip;
//     bit<48>      epoch_ingress_timestamp;
//     bit<48>      latency;
//     bit<16>      path_pkt_size;
//     // qdepth_sum_t qdepth_sum;
//     // count_t      path_count;
//     bit<32>      qdepth_sum_AND_path_count;
//     // count_t      flow_count;
//     // count_t      flow_drop;
//     bit<24>      flow_count_AND_drop;
//     // bit<3>       path_id;
//     // bit<5>       resv;
//     bit<8>       path_id_AND_src_epoch_gap;
// }

struct report_digest_t {
    bit<32>      src_ip;
    bit<32>      dst_ip;
    bit<16>      src_port;
    bit<16>      dst_port;
    bit<8>       protocol;
    bit<48>      latency;
}

struct latency_digest_t {
    bit<8>  option;
    bit<32> src_ip;
    bit<32> dst_ip;
    bit<16> src_port;
    bit<16> dst_port;
    bit<8>  protocol;
    bit<8>  flow_id_AND_conflict;
    // bit<7>  flow_id;
    // bit<1>  conflict;
    bit<48> latency0;
    bit<48> latency1;
    bit<48> latency2;
    bit<48> latency3;
    bit<48> latency4;
    bit<48> latency5;
    bit<48> latency6;
    bit<48> latency7;
}

struct digest_t {
    report_digest_t report;
    latency_digest_t latency;
}

struct learn_t {
    bit<48> srcAddr;
    bit<9>  ingress_port;
}

struct ECMP_t {
    bit<16> num_nhops;
    bit<8>  weight0;
    bit<8>  weight1;
    bit<20> bit0;
    bit<20> bit1;
}

struct register_t {
    bit<32> index;
    bit<16> path_pkt_size;
    count_t path_last_count;
    count_t flow_last_count;
    bit<4>  flow_last_epoch;
}

struct metadata {
    learn_t            learn;
    register_t         R;
    digest_t           D;
    int_metadata_t     int_meta;
    path_id_hash_t     path_hash;
    egress_metadata_t  e;
    ingress_metadata_t i;
    clone_t            c;
    latency_t          L;
    parser_metadata_t  parser_metadata;
    ECMP_t             ECMP;

    bool               mark_to_drop;

    bit<8>             instance_type;
    bit<16>            l4_dst_port;
    bit<16>            l4_src_port;
    bit<14>            ecmp_hash;
    bit<14>            ecmp_group_id;
 
    bit<32>            dst_swid;
    bit<32>            src_swid;
 
    bit<48>            sample_interval;
    bit<48>            i_last_timestamp;
    count_t            i_last_count;
 
    bit<32>            global_path_id;
 
    bit<32>            recir_index;
    bit<32>            recir_start_index;
    // bit<48>            last_notice_timestamp;
    bit<1>             mark_to_report;
    bit<48>            latency_threshold;
    bit<32>            flow_id; // actually bit<4>

    bit<48>            drop_count;

    bit<16>            src_port;
    bit<16>            dst_port;
    bit<9>             port_num;
}

#define MD_HS 6
header metadata_temp_t {
    bool    load_latency;
    bool    flow_id_hash_conflict;
    bool    abnormal_detected;
    bool    load_telemetry;
    bool    is_sink;
    bit<8>  ring_buffer_count;
    // bit<3>  resv;
    bit<32> flow_id;
    bit<32> srcAddr;
    bit<32> dstAddr;

    bit<48> latency0;
    bit<48> latency1;
    bit<48> latency2;
    bit<48> latency3;
    bit<48> latency4;
    bit<48> latency5;
    bit<48> latency6;
    bit<48> latency7;
    bit<3>  latency_count;
}

header vlan_tag_h {
    bit<3>  pcp;
    bit<1>  cfi;
    bit<12> vid;
    bit<16> ether_type;
}


error { IPHeaderTooShort }

#endif