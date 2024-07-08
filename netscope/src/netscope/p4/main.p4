/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#include "include/defines.p4"
#include "include/int_defines.p4"
#include "include/headers.p4"
#include "include/int_headers.p4"
#include "include/int_source_sink.p4"
#include "include/parsers.p4"

#define SW_NUM 50
#define PATH_PER_FLOW 8
#define PATH_ID_SIZE 8  // bit<3>
#define FLOW_ID_SIZE 16 // bit<4>

// #define BUFFER_SIZE PATH_ID_SIZE * FLOW_ID_SIZE
#define BUFFER_SIZE 81

// index
#define Buffer_I 0
#define Recirculate_I 1
#define Recirculate_Start_I 2
#define Buffer_Lock_I 3

#define DROP_THRESHOLD 1

#define PacketBuffer_Limit 300 // 512

#define DEFAULT_latency_threshold 281474976710655
// #define DEFAULT_latency_threshold 1
#define Report_Interval 50 * 60 * 1000 * 10

/* There's some noise packet when tcpreplay, whose latency is much higher than
   packets in the experiment. Set a max latency to filter out the noise packets. */
#define MAX_LATENCY 10000000000

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {   
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    register<bit<48>>(2) last_notice_timestamp;
    register<bit<48>>(SW_NUM) src_timestamps;
    register<count_t>(SW_NUM) src_counts;

    register<bit<20>>(SW_NUM*2) ECMP_bit; // bit counter

    register<bit<4>>(SW_NUM) src_epoch_reg;

    action drop() {
        meta.mark_to_drop = true;
        mark_to_drop(standard_metadata);
    }

    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops){
        hash(meta.ecmp_hash,
            HashAlgorithm.crc16,
            (bit<1>)0,
            {   
                // standard_metadata.ingress_global_timestamp, 
                // add timestamp so that same flow will go to different path
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr,
                meta.src_port,
                meta.dst_port,
                hdr.ipv4.protocol},
            num_nhops);
	    meta.ecmp_group_id = ecmp_group_id;
        meta.ECMP.num_nhops = num_nhops;
    }

    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ecmp_group_to_nhop {
        key = {
            meta.ecmp_group_id: exact;
            meta.ecmp_hash: exact;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 1024;
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            set_nhop;
            ecmp_group;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    action set_ECMP_weights(bit<8> weight0, bit<8> weight1){
        meta.ECMP.weight0 = weight0;
        meta.ECMP.weight1 = weight1;
    }
    table get_ECMP_weight {
        key = {
            // hdr.ipv4.dstAddr: lpm;
        }
        actions = {set_ECMP_weights;}
        default_action = set_ECMP_weights(1, 1);
    }

    action set_dst_swid(bit<32> swid){meta.dst_swid = swid;}
    table get_dst_swid {
        key = {hdr.ipv4.dstAddr: lpm;}
        actions = {set_dst_swid;}
        default_action = set_dst_swid(SW_NUM-1);
    }

    action set_sample_interval(bit<48> sample_interval){meta.sample_interval = sample_interval;}
    table get_sample_interval {
        key = {}
        actions = {set_sample_interval;}
        default_action = set_sample_interval(1000);
    }

    action set_swid_ingress(bit<16> swid) {meta.int_meta.swid = swid;}
    table get_swid_ingress {
        key = {}
        actions = {set_swid_ingress;NoAction;}
        default_action = NoAction;
    }

    action insert_debug_data() {
        // insert debug header
        hdr.debug.push_front(1);
        hdr.debug[0].setValid();

        // update lenghth
        hdr.debug_shim.count = hdr.debug_shim.count + 1;
        hdr.udp.length_ = hdr.udp.length_ + (bit<16>)DEBUG_HS;
	    hdr.ipv4.totalLen = hdr.ipv4.totalLen + (bit<16>)DEBUG_HS;

        // udpate debug data
        
        // hdr.debug[0].meta_ingress_port = meta.path_hash.ingress_port;
        // hdr.debug[0].meta_egress_port = meta.path_hash.egress_port;
        hdr.debug[0].swid = meta.int_meta.swid;
        // hdr.debug[0].qdepth = (bit<16>)standard_metadata.deq_qdepth;
    }

    action set_port_num(bit<9> n) {meta.port_num = n;}
    table get_port_num {
        key = {}
        actions = {set_port_num;}
        default_action = set_port_num(0);
    }


    // INGRESS APPLY
    apply {
        // get sw_id
        get_swid_ingress.apply();
        get_port_num.apply();
        if (!hdr.md.isValid()) {hdr.md.setValid();}

        if (meta.int_meta.swid == 0 && hdr.ipv4_option.option == IPV4_OPTION_NOTICE) {
            meta.D.report.src_ip = hdr.ipv4.srcAddr;
            meta.D.report.dst_ip = hdr.ipv4.dstAddr;
            meta.D.report.src_port = meta.src_port;
            meta.D.report.dst_port = meta.dst_port;
            meta.D.report.protocol = hdr.ipv4.protocol;
            meta.D.report.latency = hdr.int_shim.latency;

            digest<report_digest_t>(1, meta.D.report);
        }

        // if (standard_metadata.ingress_port > meta.port_num) {
        if (standard_metadata.ingress_port == 0 || standard_metadata.ingress_port > meta.port_num) {
            drop();
        }

        // Check wheather it is a source/sink node,
        detect_int_source_sink.apply(hdr, meta, standard_metadata);

        // Add Debug Header
        if (meta.int_meta.source && DEBUG && (!hdr.debug_shim.isValid())) {
            hdr.debug_shim.setValid();
            hdr.debug_shim.count = 0;

            hdr.ipv4.totalLen = hdr.ipv4.totalLen + DEBUG_SHIM_HS;
            hdr.udp.length_ = hdr.udp.length_ + DEBUG_SHIM_HS;
        }
        if (DEBUG) {
            insert_debug_data();
        }

        if (meta.int_meta.source && hdr.ipv4.ihl == 5) {
            // IPv4 Option
            hdr.ipv4.ihl = 6;
            hdr.ipv4_option.setValid();

            hdr.ipv4_option.copyFlag = 0;
            hdr.ipv4_option.optClass = 0; // control
            hdr.ipv4_option.option = 0;
            hdr.ipv4_option.optionLength = 4;

            hdr.ipv4_option.src_count = 0;
            hdr.ipv4_option.path_id = 0;
            hdr.ipv4_option.abnormal_detected = false;
            
            hdr.ipv4.totalLen = hdr.ipv4.totalLen + IPV4_OPTION_HS;
            // insert_ipv4_option();
        }

        // -----------------------------------------------------------------------

        // Recirculate case
        if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_INGRESS_RECIRC) { 
        }


        // Note packet as normal type
        if (hdr.ipv4_option.option == IPV4_OPTION_NOTICE
            && standard_metadata.instance_type == PKT_INSTANCE_TYPE_NORMAL 
            ) {
            // do nothing, let the remote notice go to egress and trigger clone.
            hdr.debug[0].state_i = 7;
        }  
        // Note packet
        else if ((meta.i.notice_recir) ||
                // ========== Start a Notice Packet from here ========== (Recirculate notice packet)
                ((hdr.ipv4_option.option == IPV4_OPTION_NOTICE) && (meta.int_meta.swid!=0))
                // ========== Receive a Notice Packet from other ==========
                ) {
        } 
        // Report by digest
        else if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_INGRESS_RECIRC
                 && hdr.ipv4_option.option == IPV4_OPTION_INT_REPORT
                 && hdr.int_report.isValid()
                 ) {
        }
        // ========== Not Notice Packet (Normal Packet) ==========
        // or s0 recieve a notice packet for debug
        else if (hdr.ipv4_option.option==0) {
            hdr.debug[0].state_i = 4;
            // TODO: what if pkt's ipv4 doesn't has option data

            standard_metadata.priority = hdr.ipv4.diffserv_priority; // priority

            // ==================== Source Node =========================
            if (meta.int_meta.source) {
                hdr.debug[0].state_i = 5;
                get_dst_swid.apply();
                get_sample_interval.apply();
                src_timestamps.read(meta.i_last_timestamp, meta.dst_swid);
                src_counts.read(meta.i_last_count, meta.dst_swid);
                src_epoch_reg.read(meta.i.epoch, meta.dst_swid);

                if ((standard_metadata.ingress_global_timestamp - (bit<48>)meta.sample_interval > meta.i_last_timestamp) && 
                    (standard_metadata.ingress_global_timestamp > meta.i_last_timestamp)){
                    // Set it as an INT packet
                    int_source_init.apply(hdr, meta, standard_metadata);
                    
                    
                    hdr.int_shim.src_epoch = meta.i.epoch;
                    src_epoch_reg.write(meta.dst_swid, meta.i.epoch + 1);

                    // INT normal packet data
                    hdr.ipv4_option.src_count = meta.i_last_count + 1;

                    // Update last timestamp
                    src_timestamps.write(meta.dst_swid, standard_metadata.ingress_global_timestamp);
                    // Reset counter
                    src_counts.write(meta.dst_swid, 0);

                } else {
                    // TODO: what if counts exceed
                    hdr.ipv4_option.src_count = meta.i_last_count + 1;
                    src_counts.write(meta.dst_swid, hdr.ipv4_option.src_count);
                }
            }

        } else {
            hdr.debug[0].state_i = 6;
        }

        // ---------------------------------------------------------------------------------
        // Basic Forward Work
        // (Unlike clone with `mirror_port`, recirculate need to update dst in specially)
        switch (ipv4_lpm.apply().action_run) {
            ecmp_group: { // more than one path to go (select)
                if (hdr.ipv4_option.option != IPV4_OPTION_NOTICE 
                    && hdr.ipv4_option.option != IPV4_OPTION_INT_REPORT
                    ) { 
                    /* exclude NOTICE and REPORT pkt, and LATENCY is specific for s0, 
                       ecmp_group action will not be triggered. So here only consider
                       normal packets (INT, raw).
                    */
                    // #define ECMP_RESET_PERIOD 10000000*100
                    // if (meta.ECMP.num_nhops == 2) { // For now, only consider 2 paths
                    //     ECMP_bit.read(meta.ECMP.bit0, meta.dst_swid*2 + 0);
                    //     ECMP_bit.read(meta.ECMP.bit1, meta.dst_swid*2 + 1);
                    //     get_ECMP_weight.apply();
                    //     bit<32> bit0 = (bit<32>)(meta.ECMP.bit0 * (bit<20>)meta.ECMP.weight1);
                    //     bit<32> bit1 = (bit<32>)(meta.ECMP.bit1 * (bit<20>)meta.ECMP.weight0);

                    //     bit<48> last_ECMP_t;
                    //     last_notice_timestamp.read(last_ECMP_t, 1);
                    //     // reset counter
                    //     if ((ECMP_RESET_PERIOD < standard_metadata.ingress_global_timestamp - last_ECMP_t) 
                    //         || (meta.ECMP.bit0 > (1<<20 - 1)) || (meta.ECMP.bit1 > (1<<20 - 1))) {
                    //         meta.ECMP.bit0 = 0;
                    //         meta.ECMP.bit1 = 0;
                    //         // reset timestamp
                    //         last_notice_timestamp.write(1, standard_metadata.ingress_global_timestamp);
                    //         ECMP_bit.write(meta.dst_swid*2 + 0, meta.ECMP.bit0);
                    //         ECMP_bit.write(meta.dst_swid*2 + 1, meta.ECMP.bit1);
                    //     }

                    //     if (bit0 > bit1) {
                    //         meta.ecmp_hash = 1;
                    //         ECMP_bit.write(meta.dst_swid*2 + 1, meta.ECMP.bit1 + (bit<20>)hdr.ipv4.totalLen);
                    //     } else {
                    //         meta.ecmp_hash = 0;
                    //         ECMP_bit.write(meta.dst_swid*2 + 0, meta.ECMP.bit0 + (bit<20>)hdr.ipv4.totalLen);
                    //     }

                    //     // if (bit0 < bit1) {
                    //     //     meta.ecmp_hash = 0;
                    //     //     ECMP_bit.write(meta.dst_swid*2 + 0, meta.ECMP.bit0 + (bit<20>)hdr.ipv4.totalLen);
                    //     // } else {
                    //     //     meta.ecmp_hash = 1;
                    //     //     ECMP_bit.write(meta.dst_swid*2 + 1, meta.ECMP.bit1 + (bit<20>)hdr.ipv4.totalLen);
                    //     // }

                    //     // hdr.debug[0].tstamp = (bit<48>)bit0;
                    //     // hdr.debug[0].tstamp2 = (bit<48>)bit1;
                    // }
                }
                ecmp_group_to_nhop.apply();
            }
        }

        if (hdr.int_shim.isValid() && hdr.int_shim.src_timestamp == 0) {
            mark_to_drop(standard_metadata);
            meta.mark_to_drop = true;
        }

        // hdr.debug[0].option = (bit<8>) hdr.ipv4_option.option;
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    // Counts
    register<count_t>(SW_NUM) flow_counts;
    register<bit<4>>(SW_NUM) flow_epochs;
    register<count_t>(SW_NUM*PATH_PER_FLOW) path_counts;
    register<bit<16>>(SW_NUM*PATH_PER_FLOW) path_pkt_sizes;
    
    // Index for xxx
    register<bit<32>>(4) buffer_index_reg;

    // Ring Buffer for Telemetry Data
    register<count_t>(BUFFER_SIZE)      buffer_path_count;
    register<count_t>(BUFFER_SIZE)      buffer_flow_count;
    register<count_t>(BUFFER_SIZE)      buffer_flow_drop;
    register<bit<48>>(BUFFER_SIZE)      buffer_src_tstamp;
    register<bit<48>>(BUFFER_SIZE)      buffer_latency;
    register<qdepth_sum_t>(BUFFER_SIZE) buffer_qdepth;
    register<bit<32>>(BUFFER_SIZE)      buffer_dst_ip;
    register<bit<32>>(BUFFER_SIZE)      buffer_src_ip;
    register<bit<3>>(BUFFER_SIZE)       buffer_path_id;
    register<bit<16>>(BUFFER_SIZE)      buffer_path_pkt_size;
    register<bit<4>>(BUFFER_SIZE)       buffer_flow_src_epoch_gap;
    
    #define T_REPORT_I 0
    #define T_NOTICE_I 1
    #define DROP_I 2
    register<bit<48>>(3) last_tstamp;

    // Latency Buffer
    register<bit<48>>(FLOW_ID_SIZE * Latency_List_LEN) latency_list;
    register<bit<3>>(FLOW_ID_SIZE) latency_list_index;
    register<bit<32>>(FLOW_ID_SIZE) latency_list_dst_ip;
    register<bit<32>>(FLOW_ID_SIZE) latency_list_src_ip;
    
    // TODO: lock flag: only one recirculate is allowed to run 

    action set_src_swid(bit<32> swid) {meta.src_swid = swid;}
    table get_src_swid{
        key = {hdr.ipv4.srcAddr: lpm;}
        actions = {set_src_swid;}
        default_action = set_src_swid(SW_NUM-1);
    }

    action set_swid(bit<16> swid) {
        meta.int_meta.swid = swid;
    }
    table get_swid{
        key = {}
        actions = {set_swid;NoAction;}
        default_action = NoAction;
    }
    
    // action insert_debug_data() {
    //     // insert debug header
    //     hdr.debug.push_front(1);
    //     hdr.debug[0].setValid();

    //     // update lenghth
    //     hdr.debug_shim.count = hdr.debug_shim.count + 1;
    //     hdr.udp.length_ = hdr.udp.length_ + (bit<16>)DEBUG_HS;
	//     hdr.ipv4.totalLen = hdr.ipv4.totalLen + (bit<16>)DEBUG_HS;

    //     // udpate debug data
        
    //     // hdr.debug[0].meta_ingress_port = meta.path_hash.ingress_port;
    //     // hdr.debug[0].meta_egress_port = meta.path_hash.egress_port;
    //     hdr.debug[0].swid = meta.int_meta.swid;
    //     // hdr.debug[0].qdepth = (bit<16>)standard_metadata.deq_qdepth;
    // }


    action hash_path_id() {
        hash(
            hdr.ipv4_option.path_id,
            HashAlgorithm.crc16,
            (bit<1>)0,
            {
                hdr.ipv4_option.path_id,
                meta.int_meta.swid,
                meta.path_hash.ingress_port,
                meta.path_hash.egress_port
                // meta.path_hash.path_hash_control
            },
            (bit<16>)8
        );
        hdr.ipv4_option.path_id = (bit<3>)((hdr.ipv4_option.path_id + meta.path_hash.path_hash_control));
    }

    action truncate_pkt(bit<32> len) {
        bit<32> truncate_len;
        if (DEBUG) {
            truncate_len = len + DEBUG_SHIM_HS + (bit<32>)hdr.debug_shim.count * DEBUG_HS;
        } else {
            truncate_len = len;
        }
        // truncate(truncate_len); //bytes
        // hdr.ipv4.totalLen = (bit<16>)truncate_len - ETH_HS;
        // hdr.udp.length_ = (bit<16>)truncate_len - (UDP_LEN - UDP_HS);
    }

    action report_header_init() {
        // Change destination
        hdr.ipv4.dstAddr = meta.e.collector_ip;
        // Tag it is report pkt
        hdr.ipv4_option.option = IPV4_OPTION_INT_REPORT; 

        hdr.int_shim.setInvalid();

        truncate_pkt(UDP_LEN + INT_SHIM_HS + INT_REPORT_HS);
    }

    action init_latency_pkt() {
        // Change destination
        hdr.ipv4.dstAddr = meta.e.collector_ip;
        // Tag it is latency pkt
        hdr.ipv4_option.option = IPV4_OPTION_LATENCY;

        hdr.int_shim.setInvalid();

        truncate_pkt(UDP_LEN + Latency_SHIM_HS + Latency_HS * Latency_List_LEN);
    }

    action init_notice_pkt(){
        // Tag it is notice pkt
        hdr.ipv4_option.option = IPV4_OPTION_NOTICE; 

        hdr.int_shim.setInvalid();

        truncate_pkt(UDP_LEN);
    }

    action set_path_hash_control(bit<3> path_hash_control) {
        meta.path_hash.path_hash_control = path_hash_control;
    }

    table get_path_hash_control{
        key = {
            meta.src_swid: exact;
            meta.dst_swid: exact;
            meta.path_hash.egress_port: exact;
            hdr.ipv4_option.path_id: exact;
        }
        actions = {
            set_path_hash_control;
        }
        default_action = set_path_hash_control(0);
    }

    action get_flow_id(){
        hash(meta.flow_id,
            HashAlgorithm.crc32, // test
            (bit<1>)0,
            {   
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr,
                meta.src_port,
                meta.dst_port,
                hdr.ipv4.protocol},
            (bit<16>)16); // 16 = 0b1111 (4b)
    }

    action set_latency_threshold(bit<48> threshold){meta.latency_threshold = threshold;}
    action set_default_latency_threshold(){meta.latency_threshold = DEFAULT_latency_threshold;}
    table get_latency_threshold{
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
            meta.src_port: exact;
            meta.dst_port: exact;
            hdr.ipv4.protocol: exact;
        }
        actions = {set_latency_threshold;set_default_latency_threshold;}
        default_action = set_default_latency_threshold;
    }

    table get_latency_threshold_host{
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
        }
        actions = {set_latency_threshold;set_default_latency_threshold;}
        default_action = set_default_latency_threshold;
    }

    table get_latency_threshold_edge_sw{
        key = {
            meta.src_swid: exact;
            meta.dst_swid: exact;
        }
        actions = {set_latency_threshold;set_default_latency_threshold;}
        default_action = set_default_latency_threshold;
    }

    table get_short_latency_threshold{
        key = {}
        actions = {set_latency_threshold;set_default_latency_threshold;}
        default_action = set_default_latency_threshold;
    }

    action set_collector_ip(ip4Addr_t ip4DstAddr){meta.e.collector_ip = ip4DstAddr;}
    table get_collector_ip{
        key = { }
        actions = {set_collector_ip; NoAction;}
        default_action = NoAction;
    }

    // [E] EGRESS APPLY
    apply {
    if (hdr.udp.isValid()) {
        meta.src_port = hdr.udp.src_port;
        meta.dst_port = hdr.udp.dst_port;
    } else if (hdr.tcp.isValid()) {
        meta.src_port = hdr.tcp.src_port;
        meta.dst_port = hdr.tcp.dst_port;
    }

    get_swid.apply();
    // if (DEBUG) { 
    //     insert_debug_data();
    // }
    hdr.debug[0].state = 10;
    if (meta.int_meta.swid == 0) {
        hdr.debug[0].state = 9;
        // do nothing
    } else if (meta.mark_to_drop != true) {
        hdr.debug[0].state = 11;
        if (!hdr.md.isValid()) {hdr.md.setValid();}
        
        // hdr.debug[0].L_idx = (bit<3>) standard_metadata.instance_type;
        
        /*
         * <<<<<<<<<<<<<<<<<<<<<=====================>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<< Multicast Replication >>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<=====================>>>>>>>>>>>>>>>>>>>>>>>>
         Forward Notice Packet (from Ingress)
         */
        if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_REPLICATION) {
            hdr.debug[0].state = 6;
        }

        /*
         * <<<<<<<<<<<<<<<<<<<<<====================>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<==== Reciculate ====>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<====================>>>>>>>>>>>>>>>>>>>>>>>>
         recirculate flag only valid in ingress, need a metadata to keep the flag
         */
        else if (meta.instance_type == PKT_INSTANCE_TYPE_INGRESS_RECIRC) {
            //>============= Report Recirculate ===============
            if (hdr.ipv4_option.option == IPV4_OPTION_INT_REPORT) {
                hdr.debug[0].state = 2;
            }

            //>============= Notice Recirculate ===============
            else if (hdr.ipv4_option.option == IPV4_OPTION_NOTICE) {
                hdr.debug[0].state = 4;
                // should not go to here
            }
        }
        else if (hdr.ipv4_option.option == IPV4_OPTION_LATENCY) {
            hdr.debug[0].state = 3;
            // should not go to here
        }

        /*
         * <<<<<<<<<<<<<<<<<<<<<=====================>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<======= Clone =======>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<=====================>>>>>>>>>>>>>>>>>>>>>>>>
         */
        else if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_EGRESS_CLONE) {
            hdr.debug[0].state = 5;
            
            get_collector_ip.apply();

            hdr.int_shim.setInvalid();

            // [N] >================= Notice Packet: Start 1st  ===============
            if (hdr.md.abnormal_detected) {
                init_notice_pkt();
                hdr.ipv4.dstAddr = meta.e.collector_ip;

                hdr.md.abnormal_detected = false; // reset
                
                hdr.ipv4_option.src_count = 0;
                // recirculate(standard_metadata);

                if (hdr.md.load_latency || hdr.md.flow_id_hash_conflict){ // clone to load latency
                    clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
                }
            }
            
            
            // [R] >================= Report Packet: config header, before recirculate ===============
            // else if (hdr.md.load_telemetry) {
                // report_header_init();
                
                
            //     // re-use this field to record ring buffer count
            //     hdr.ipv4_option.src_count = 0;
            //     hdr.ipv4_option.path_id = (bit<3>) meta.int_meta.swid;
                                
            //     hdr.md.load_telemetry = false; // reset
            //     if (hdr.md.load_latency || hdr.md.flow_id_hash_conflict){ // clone to load latency
            //         clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
            //     }

            //     // last_report_timestamp_reg.write(0, standard_metadata.ingress_global_timestamp);

            //     // begin to load telemetry
            //     recirculate(standard_metadata);
            // }


            // [R] >================= Report Packet: config header, before recirculate ===============
            // else if (hdr.md.load_telemetry) {
                // report_header_init();
                
                
            //     // re-use this field to record ring buffer count
            //     hdr.ipv4_option.src_count = 0;
            //     hdr.ipv4_option.path_id = (bit<3>) meta.int_meta.swid;
                                
            //     hdr.md.load_telemetry = false; // reset
            //     if (hdr.md.load_latency || hdr.md.flow_id_hash_conflict){ // clone to load latency
            //         clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
            //     }

            //     // last_report_timestamp_reg.write(0, standard_metadata.ingress_global_timestamp);

            //     // begin to load telemetry
            //     recirculate(standard_metadata);
            // }

            // [L] >================= Latency Packet ===============
            else if (hdr.md.load_latency || hdr.md.flow_id_hash_conflict) {
                // hdr.ipv4_option.option = IPV4_OPTION_LATENCY;
                init_latency_pkt();

                meta.flow_id = hdr.md.flow_id;

                // latency_shim_header
                hdr.latency_shim.setValid();
                hdr.latency_shim.src_ip = hdr.md.srcAddr;
                hdr.latency_shim.dst_ip = hdr.md.dstAddr;
                hdr.latency_shim.src_port = meta.src_port;
                hdr.latency_shim.dst_port = meta.dst_port;
                hdr.latency_shim.protocol = hdr.ipv4.protocol;
                hdr.latency_shim.flow_id = (bit<7>) hdr.md.flow_id; // though actually bit<4>
                
                hdr.latency_data.push_front(8);
                hdr.latency_data[0].setValid(); hdr.latency_data[0].latency = hdr.md.latency0;
                hdr.latency_data[1].setValid(); hdr.latency_data[1].latency = hdr.md.latency1;
                hdr.latency_data[2].setValid(); hdr.latency_data[2].latency = hdr.md.latency2;
                hdr.latency_data[3].setValid(); hdr.latency_data[3].latency = hdr.md.latency3;
                hdr.latency_data[4].setValid(); hdr.latency_data[4].latency = hdr.md.latency4;
                hdr.latency_data[5].setValid(); hdr.latency_data[5].latency = hdr.md.latency5;
                hdr.latency_data[6].setValid(); hdr.latency_data[6].latency = hdr.md.latency6;
                hdr.latency_data[7].setValid(); hdr.latency_data[7].latency = hdr.md.latency7;
  
            
                bit<32> index; bit<48> latency;
                if (hdr.md.flow_id_hash_conflict){ // TODO: test to check
                    // Since index point to new flow, and latency header contain the old flow，
                    // save the index value to tell control plane where to stop reading data.
                    // count = index + 1 (begin from 0)
                    hdr.ipv4_option.src_count = (count_t) hdr.md.latency_count + 1;

                    hdr.latency_shim.conflict = 1;
                } else {
                    // re-use count field.
                    hdr.ipv4_option.src_count = 8;
                }
            }
            else {
                // in case of unkonw issue
                // mark_to_drop(standard_metadata);
            }
        }


        /* 
         * <<<<<<<<<<<<<<<<<<<<<=====================>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<======= Normal ======>>>>>>>>>>>>>>>>>>>>>>>>
         * <<<<<<<<<<<<<<<<<<<<<=====================>>>>>>>>>>>>>>>>>>>>>>>>
         */
        else if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_NORMAL) {
            hdr.debug[0].state = 7;
            if (hdr.ipv4_option.option == IPV4_OPTION_INT_REPORT) {
                // should not go to here
            }
            else if (hdr.ipv4_option.option == IPV4_OPTION_LATENCY) {
                // should not go to here
            }
            //>============= Receive Remote Notice ===============
            else if (hdr.ipv4_option.option == IPV4_OPTION_NOTICE) {
                hdr.debug[0].state = 12;
                
                // bit<48> last_notice_t;
                // last_tstamp.read(last_notice_t, T_NOTICE_I);
                // if (standard_metadata.ingress_global_timestamp - last_notice_t > Report_Interval){
                //     // check report lock
                //     // bit<32> buffer_read_count;
                //     // buffer_index_reg.read(buffer_read_count, Buffer_Lock_I);
                //     // if (buffer_read_count == 0) { // unlock
                //         // buffer_index_reg.write(Buffer_Lock_I, 1); // lock
                        
                //         // hdr.md.load_telemetry = true;
                //         hdr.md.abnormal_detected = true;
                //         clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);

                //         // debug
                //         // last_tstamp.write(T_NOTICE_I, standard_metadata.ingress_global_timestamp);
                //     // }
                // }
                
                // // Notice pkt's life is noly one hop
                // mark_to_drop(standard_metadata);
            }
            //>============= Normal(Naive/INT) Business Packet ===============
            else {
                get_src_swid.apply();
                
                //>================= [Both] INT or Normal Packet ===============
                {// update hdr.ipv4_option.path_id by hash
                    if (meta.int_meta.source) { 
                        meta.path_hash.ingress_port = 0; 
                    } else { 
                        meta.path_hash.ingress_port = standard_metadata.ingress_port; 
                    }

                    if (meta.int_meta.sink) { 
                        meta.path_hash.egress_port = 0; 
                    } else { 
                        meta.path_hash.egress_port = standard_metadata.egress_port; 
                    }
                    // get data
                    get_path_hash_control.apply();
                    // get_swid.apply();

                    // hash path id
                    hash_path_id();
                }
                
                bit<48> latency = 0;


                //>================= Special for INT Packet ===============
                if (hdr.ipv4_option.option == IPV4_OPTION_INT) {
                    // get_latency_threshold.apply();
                    // if (!get_latency_threshold.apply().hit) {
                    //     /* fail to get latency threshold according to flow information,
                    //        which means that this flow is a short flow, 
                    //        as it lack history to get its threshold. */
                    //     if (!get_latency_threshold_host.apply().hit) {
                    //         get_short_latency_threshold.apply();
                    //     }
                    // }

                    // flow id (5-tuple)
                    switch (get_latency_threshold.apply().action_run) {
                        set_default_latency_threshold: {
                            // host level
                            switch (get_latency_threshold_host.apply().action_run) {
                                set_default_latency_threshold: {
                                    // edge switch level
                                    switch (get_latency_threshold_edge_sw.apply().action_run) {
                                        set_default_latency_threshold : {
                                            // simple short flow level
                                            get_short_latency_threshold.apply();
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // 
                    // Update INT Shim header per hop
                    // hdr.int_shim.qdepth_sum = hdr.int_shim.qdepth_sum + (qdepth_sum_t)standard_metadata.deq_qdepth;// + (qdepth_sum_t)standard_metadata.enq_qdepth;
                    hdr.int_shim.qdepth_sum = hdr.int_shim.qdepth_sum + (qdepth_sum_t)standard_metadata.enq_qdepth;

                    // Abnormal Detection: check latency is over threshold. 
                    latency = standard_metadata.egress_global_timestamp - hdr.int_shim.src_timestamp;
                    if (latency >= meta.latency_threshold && latency < MAX_LATENCY){
                        // only when the pkt didn't trigger NOTICE pkt, then it will trigger NOTICE pkt here.
                        if (!hdr.ipv4_option.abnormal_detected) { // debug
                            // clone to init a notice packet
                            hdr.md.abnormal_detected = true;
                            hdr.md.load_telemetry = true;
                            hdr.ipv4_option.abnormal_detected = true;
                            clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);

                            // hdr.debug[0].tstamp = latency;
                        }
                    }
                    // hdr.debug[0].timestamp = meta.latency_threshold;

                    if (DEBUG) {
                        hdr.debug[0].timestamp = meta.latency_threshold;
                        hdr.debug[0].enq_timestamp = (bit<32>)latency;

                        hdr.debug[0].swid = meta.int_meta.swid;
                        hdr.debug[0].ingress_port = standard_metadata.ingress_port;
                        hdr.debug[0].egress_port = standard_metadata.egress_port;
                        // hdr.debug[0].timestamp = standard_metadata.ingress_global_timestamp;
                        hdr.debug[0].qdepth = (bit<16>)standard_metadata.enq_qdepth;
                        hdr.debug[0].packet_length = standard_metadata.packet_length;
                        // hdr.debug[0].enq_timestamp = standard_metadata.enq_timestamp;
                        hdr.debug[0].deq_timedelta = standard_metadata.deq_timedelta;
                        hdr.debug[0].enq_qdepth = standard_metadata.enq_qdepth;
                    }


                    //>>============ INT Packet > Sink Node ===============
                    if (meta.int_meta.sink) {
                        // process_int_sink.apply(hdr, meta, standard_metadata); // comment

                        // update latency
                        // hdr.int_shim.latency = standard_metadata.egress_global_timestamp - hdr.int_shim.src_timestamp;
                    }
                    
                    //>>============ INT Packet > Source/Transit Node ===============
                    else {
                        // do nothing else.
                    }
                }


                //>>================ [Both] INT or Normal Packet: Sink ===============
                if (meta.int_meta.sink) {
                    hdr.md.is_sink = meta.int_meta.sink;

                    
                    meta.global_path_id = (meta.src_swid - 1) * PATH_PER_FLOW + (bit<32>)hdr.ipv4_option.path_id;
                    
                    flow_counts.read(meta.R.flow_last_count, meta.src_swid);
                    path_counts.read(meta.R.path_last_count, meta.global_path_id);
                    path_pkt_sizes.read(meta.R.path_pkt_size, meta.global_path_id);
                    
                    meta.R.flow_last_count = meta.R.flow_last_count + 1;
                    meta.R.path_last_count = meta.R.path_last_count + 1;
                    meta.R.path_pkt_size = meta.R.path_pkt_size + hdr.ipv4.totalLen/4;

                    flow_counts.write(meta.src_swid, meta.R.flow_last_count);
                    path_counts.write(meta.global_path_id, meta.R.path_last_count);
                    path_pkt_sizes.write(meta.global_path_id, meta.R.path_pkt_size);

                    last_tstamp.read(meta.drop_count, DROP_I);
                    // if (hdr.ipv4_option.src_count > meta.R.flow_last_count) {
                    //     count_t cout_diff;
                    //     if (hdr.ipv4_option.src_count > meta.R.flow_last_count) {
                    //         cout_diff = hdr.ipv4_option.src_count - meta.R.flow_last_count;
                    //     } else {
                    //         cout_diff = meta.R.flow_last_count - hdr.ipv4_option.src_count;
                    //     }
                    //     meta.drop_count = meta.drop_count + (bit<48>)cout_diff;
                    //     // meta.drop_count = (bit<48>)(hdr.ipv4_option.src_count - meta.R.flow_last_count);
                    //     if (
                    //         meta.drop_count >= DROP_THRESHOLD && 
                    //         !hdr.ipv4_option.abnormal_detected
                    //         ) { // debug
                    //         // clone to init a notice packet
                    //         hdr.md.abnormal_detected = true;
                    //         hdr.md.load_telemetry = true;
                    //         hdr.ipv4_option.abnormal_detected = true;
                    //         clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
                    //         last_tstamp.write(DROP_I, 0);
                    //     }
                    // }

                    // INT packets
                    latency = standard_metadata.egress_global_timestamp - hdr.int_shim.src_timestamp;
                    if (latency < MAX_LATENCY && hdr.ipv4_option.isValid() && hdr.int_shim.isValid() && hdr.ipv4_option.option == IPV4_OPTION_INT) { // insert buffer

                        hdr.int_shim.latency = latency;


                        buffer_index_reg.read(meta.R.index, Buffer_I);
                        // hdr.debug[0].resv2 = (bit<16>) meta.recir_index + 30;

                        buffer_path_count.write(meta.R.index, meta.R.path_last_count);
                        buffer_flow_count.write(meta.R.index, hdr.ipv4_option.src_count);
                        // buffer_flow_drop.write(meta.R.index, hdr.ipv4_option.src_count - meta.R.flow_last_count);
                        buffer_flow_drop.write(meta.R.index, meta.R.flow_last_count);
                        buffer_latency.write(meta.R.index, latency);
                        buffer_src_ip.write(meta.R.index, hdr.ipv4.srcAddr);
                        buffer_dst_ip.write(meta.R.index, hdr.ipv4.dstAddr);
                        buffer_qdepth.write(meta.R.index, hdr.int_shim.qdepth_sum);
                        buffer_path_id.write(meta.R.index, hdr.ipv4_option.path_id);
                        buffer_path_pkt_size.write(meta.R.index, meta.R.path_pkt_size);
                        // write tstamp at last (in case of conflict with controll plane's reset action)
                        buffer_src_tstamp.write(meta.R.index, hdr.int_shim.src_timestamp);

                        flow_epochs.read(meta.R.flow_last_epoch, meta.src_swid);
                        bit<4> src_last_epoch = hdr.int_shim.src_epoch - 1;
                        buffer_flow_src_epoch_gap.write(meta.R.index, src_last_epoch - meta.R.flow_last_epoch);
                        flow_epochs.write(meta.src_swid, hdr.int_shim.src_epoch);
                        // if (src_last_epoch != meta.R.flow_last_epoch) {
                        //     hdr.md.abnormal_detected = true;
                        //     hdr.md.load_telemetry = true;
                        //     hdr.ipv4_option.abnormal_detected = true;
                        //     clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
                        // }

                        // bit<48> epoch_ingress_timestamp;
                        // buffer_src_tstamp.read(epoch_ingress_timestamp, meta.R.index);
                        // hdr.debug[0].tstamp = epoch_ingress_timestamp;

                        meta.R.index = meta.R.index + 1;
                        if (meta.R.index >= BUFFER_SIZE) {
                            meta.R.index = 0;
                        }

                        // meta.R.index = (meta.R.index + 1) % (BUFFER_SIZE);
                        buffer_index_reg.write(Buffer_I, meta.R.index);

                        // reset counter
                        flow_counts.write(meta.src_swid, 0);
                        path_counts.write(meta.global_path_id, 0);
                        path_pkt_sizes.write(meta.global_path_id, 0);

                        // conditionally report latency to control plane.
                        { // save latency
                            get_flow_id();
                            hdr.md.flow_id = meta.flow_id; // save in metadata
                            latency_list_index.read(meta.L.idx, meta.flow_id);

                            // buffer is empty, save flow info first
                            if (meta.L.idx == 0) {
                                latency_list_src_ip.write(meta.flow_id, hdr.ipv4.srcAddr);
                                latency_list_dst_ip.write(meta.flow_id, hdr.ipv4.dstAddr);
                                meta.L.src_ip = hdr.ipv4.srcAddr;
                                meta.L.dst_ip = hdr.ipv4.dstAddr;
                            } // debug
                            else {
                                latency_list_src_ip.read(meta.L.src_ip, meta.flow_id);
                                latency_list_dst_ip.read(meta.L.dst_ip, meta.flow_id);
                            }
                            
                            // save latency
                            bit<32> offset = meta.flow_id * Latency_List_LEN;
                            latency_list.write(offset + (bit<32>)meta.L.idx, 
                                            latency);
                            
                            // update index
                            meta.L.idx = meta.L.idx + 1;
                            // meta.L.idx = (meta.L.idx + 1) % (Latency_List_LEN);
                            latency_list_index.write(meta.flow_id, meta.L.idx);                        

                            // check 5-tuple
                            if (meta.L.src_ip==hdr.ipv4.srcAddr && meta.L.dst_ip==hdr.ipv4.dstAddr) {
                                // latency buffer is full, send to control plane.
                                // index=8 is equivalent to index=0 when it is bit<3>
                                if (meta.L.idx == 0){
                                    hdr.md.load_latency = true;
                                    clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
                                }
                            } else {
                                // hash conflict
                                hdr.md.flow_id_hash_conflict = true;

                                // hdr.md.new_srcAddr = hdr.ipv4.srcAddr;
                                // hdr.md.new_dstAddr = hdr.ipv4.dstAddr;
                                hdr.md.latency_count = meta.L.idx - 1 - 1; // the last one is another flow's
                                // reset it first, in case of entering the last flow's report
                                latency_list.write(offset + (bit<32>)meta.L.idx - 1, 0);

                                clone3(CloneType.E2E, E2E_CLONE_SESSION_ID, standard_metadata);
                            }

                            if (hdr.md.load_latency || hdr.md.flow_id_hash_conflict) {
                                // save for shim
                                hdr.md.srcAddr = meta.L.src_ip;
                                hdr.md.dstAddr = meta.L.dst_ip;

                                // pre-load data
                                latency_list.read(hdr.md.latency0, offset + 0);
                                latency_list.read(hdr.md.latency1, offset + 1);
                                latency_list.read(hdr.md.latency2, offset + 2);
                                latency_list.read(hdr.md.latency3, offset + 3);
                                latency_list.read(hdr.md.latency4, offset + 4);
                                latency_list.read(hdr.md.latency5, offset + 5);
                                latency_list.read(hdr.md.latency6, offset + 6);
                                latency_list.read(hdr.md.latency7, offset + 7);
                                
                                // reset all data
                                latency_list.write(offset + 0, 0);
                                latency_list.write(offset + 1, 0);
                                latency_list.write(offset + 2, 0);
                                latency_list.write(offset + 3, 0);
                                latency_list.write(offset + 4, 0);
                                latency_list.write(offset + 5, 0);
                                latency_list.write(offset + 6, 0);
                                latency_list.write(offset + 7, 0);

                                if (hdr.md.flow_id_hash_conflict) {
                                    latency_list_src_ip.write(meta.flow_id, hdr.ipv4.srcAddr);
                                    latency_list_dst_ip.write(meta.flow_id, hdr.ipv4.dstAddr);

                                    latency_list.write(offset + 0, latency);
                                    latency_list_index.write(meta.flow_id, 1);
                                } else {
                                    latency_list_index.write(meta.flow_id, 0);
                                }
                            }
                        }
                    }

                    if (latency >= MAX_LATENCY) {
                        mark_to_drop(standard_metadata);
                    }
                    
                }


            }
        } else {
            // unkonw condition
            hdr.debug[0].state = 8;
        }

        hdr.debug[0].ingress_port = standard_metadata.ingress_port;
        hdr.debug[0].egress_port = standard_metadata.egress_port;

    }
    if (meta.mark_to_drop) { // Reason: drop in ingress will fail
        mark_to_drop(standard_metadata);
    }
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {
	update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	          hdr.ipv4.ihl,
              hdr.ipv4.diffserv_priority,
              hdr.ipv4.diffserv_rest,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.ipv4_option);
        packet.emit(hdr.udp);
        packet.emit(hdr.tcp);

        packet.emit(hdr.latency_shim);
        packet.emit(hdr.latency_data);
        
        packet.emit(hdr.int_shim);

        packet.emit(hdr.int_report);

        packet.emit(hdr.debug_shim);
        packet.emit(hdr.debug);

        // packet.emit(hdr.md);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    // EmptyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
