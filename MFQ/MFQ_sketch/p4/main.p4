/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#include "include/headers.p4"
#include "include/parsers.p4"

/* CONSTANTS */
#define SKETCH_BUCKET_LENGTH 16
#define TS_SKETCH_CELL_BIT_WIDTH 48
#define COUNT_SKETCH_CELL_BIT_WIDTH 16

#define PREV_TS_SKETCH_REGISTER(num) register<bit<TS_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) prev_lat_ts_sketch##num
#define INGR_TS_SKETCH_REGISTER(num) register<bit<TS_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) ingr_ts_sketch##num
#define EGR_TS_SKETCH_REGISTER(num) register<bit<TS_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) egr_ts_sketch##num

// #define MIN_SKETCH_REGISTER(num) register<bit<LAT_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) min_sketch##num
#define MAX_GAP_SKETCH_REGISTER(num) register<bit<TS_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) max_gap_sketch##num
#define MIN_GAP_SKETCH_REGISTER(num) register<bit<TS_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) min_gap_sketch##num
#define COUNT_SKETCH_REGISTER(num) register<bit<COUNT_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) count_sketch##num
#define DEBUG_REGISTER(num) register<bit<COUNT_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) debug_count_sketch##num


#define QUANTILE_REGISTER(num) register<bit<TS_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) lat_quantile_sketch##num
#define C_PLUS_SKETCH_REGISTER(num) register<bit<COUNT_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) c_plus_sketch##num
#define C_MINUS_SKETCH_REGISTER(num) register<bit<COUNT_SKETCH_CELL_BIT_WIDTH>>(SKETCH_BUCKET_LENGTH) c_minus_sketch##num


//  1. Update LAT_TS record, max gap and min gap;
//  2. Update count sketch (n);
// || meta.max_gap_value_sketch##num == meta.lat_ts_value_sketch##num
#define PREV_LAT_TS_RECORD(num, algorithm)  hash(meta.prev_index_sketch##num, HashAlgorithm.algorithm, (bit<16>)0, {hdr.ipv4.srcAddr, \
    hdr.ipv4.dstAddr, hdr.tcp.srcPort, hdr.tcp.dstPort, hdr.ipv4.protocol}, (bit<16>)SKETCH_BUCKET_LENGTH);\
    prev_lat_ts_sketch##num.read(meta.lat_ts_value_sketch##num, meta.prev_index_sketch##num); \
    max_gap_sketch##num.read(meta.max_gap_value_sketch##num, meta.prev_index_sketch##num); \
    min_gap_sketch##num.read(meta.min_gap_value_sketch##num, meta.prev_index_sketch##num); \
    ingr_ts_sketch##num.read(meta.temp_ingr_ts, meta.prev_index_sketch##num);\
    egr_ts_sketch##num.read(meta.temp_egr_ts, meta.prev_index_sketch##num);\
    count_sketch##num.read(meta.count_value_sketch##num, meta.prev_index_sketch##num);\
    if (( standard_metadata.egress_global_timestamp > standard_metadata.ingress_global_timestamp\
       && (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) > meta.max_gap_value_sketch##num +  meta.lat_ts_value_sketch##num)\
       && meta.lat_ts_value_sketch##num > 0){ \
        meta.max_gap_value_sketch##num = (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) - meta.lat_ts_value_sketch##num; \
    } \
    else if (( standard_metadata.egress_global_timestamp > standard_metadata.ingress_global_timestamp\
       && meta.lat_ts_value_sketch##num > meta.max_gap_value_sketch##num +  (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp))\
       && meta.lat_ts_value_sketch##num > 0){ \
        meta.max_gap_value_sketch##num =  meta.lat_ts_value_sketch##num - (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp); \
    } \
    if (( (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) > meta.lat_ts_value_sketch##num &&\
        (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) - meta.lat_ts_value_sketch##num < meta.min_gap_value_sketch##num) \
    || meta.min_gap_value_sketch##num == 0){ \
        meta.min_gap_value_sketch##num = (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) - meta.lat_ts_value_sketch##num; \
        meta.temp_ingr_ts = standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp;\
        meta.temp_egr_ts = meta.lat_ts_value_sketch##num;\
    } \
    else if(( (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) < meta.lat_ts_value_sketch##num &&\
        meta.lat_ts_value_sketch##num - (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) < meta.min_gap_value_sketch##num) \
    || meta.min_gap_value_sketch##num == 0){ \
        meta.min_gap_value_sketch##num = meta.lat_ts_value_sketch##num - (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp); \
        meta.temp_ingr_ts = standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp;\
        meta.temp_egr_ts = meta.lat_ts_value_sketch##num;\
    } \
    max_gap_sketch##num.write(meta.prev_index_sketch##num, meta.max_gap_value_sketch##num); \
    min_gap_sketch##num.write(meta.prev_index_sketch##num, meta.min_gap_value_sketch##num); \
    meta.lat_ts_value_sketch##num = (standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp); \
    prev_lat_ts_sketch##num.write(meta.prev_index_sketch##num, meta.lat_ts_value_sketch##num);\
    lat_quantile_sketch##num.read(meta.quantile_value_sketch##num, meta.prev_index_sketch##num);\
    if (meta.quantile_value_sketch##num != 0){\
        meta.count_value_sketch##num = (meta.count_value_sketch##num + 1);\
    }\
    count_sketch##num.write(meta.prev_index_sketch##num,meta.count_value_sketch##num);\
    ingr_ts_sketch##num.write(meta.prev_index_sketch##num, meta.temp_ingr_ts);\
    egr_ts_sketch##num.write(meta.prev_index_sketch##num, meta.temp_egr_ts);\
    

 #define DEBUG_RECORD(num) debug_count_sketch##num.write(meta.prev_index_sketch##num, meta.percentile_result);
// Todo: 在用quantile-lambda更新quantile时，要注意quantile的值小于lambda的情况。如果出现这样的情况，即说明出现了一个较大的maxvalue，
//       这个时候可以发一个int数据包，通过控制面reset 该行的register来重新测量quantile
 #define QUANTILE_UPDATE(num) \
    lat_quantile_sketch##num.read(meta.quantile_value_sketch##num, meta.prev_index_sketch##num);\
    if (meta.quantile_value_sketch##num == 0){\
        meta.quantile_value_sketch##num = standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp;\
        lat_quantile_sketch##num.write(meta.prev_index_sketch##num,meta.quantile_value_sketch##num);\
    }\
    else{\
        c_plus_sketch##num.read(meta.c_plus_value_sketch##num, meta.prev_index_sketch##num);\
        c_minus_sketch##num.read(meta.c_minus_value_sketch##num, meta.prev_index_sketch##num);\
        meta.lambda_value = ((meta.max_gap_value_sketch##num >> 2) + meta.min_gap_value_sketch##num ) >> 1;\
        if ((standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) < meta.quantile_value_sketch##num){ \ 
            if (meta.c_minus_value_sketch##num + 1 > meta.count_value_sketch##num - meta.percentile_result){\
                meta.quantile_value_sketch##num = meta.quantile_value_sketch##num - meta.lambda_value;\
                meta.c_plus_value_sketch##num = meta.c_plus_value_sketch##num + 1;\
            }\
            else{\
                meta.c_minus_value_sketch##num = meta.c_minus_value_sketch##num + 1;\
            }\
        } \
        else if((standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp) > meta.quantile_value_sketch##num){\
            if (meta.c_plus_value_sketch##num + 1 > meta.percentile_result){\
                meta.quantile_value_sketch##num = meta.quantile_value_sketch##num + meta.lambda_value;\
                meta.c_minus_value_sketch##num = meta.c_minus_value_sketch##num + 1;\
            }\
            else{\
                meta.c_plus_value_sketch##num = meta.c_plus_value_sketch##num + 1;\
            }\
        }\
        c_plus_sketch##num.write(meta.prev_index_sketch##num,  meta.c_plus_value_sketch##num);\
        c_minus_sketch##num.write(meta.prev_index_sketch##num, meta.c_minus_value_sketch##num);\
        lat_quantile_sketch##num.write(meta.prev_index_sketch##num, meta.quantile_value_sketch##num);\
    }
    


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
    
    action drop(){
        mark_to_drop(standard_metadata);
    }
    action set_egress_port(bit<9> egress_port){
        standard_metadata.egress_spec = egress_port;
    }
    table forwarding {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            set_egress_port;
            drop;
            NoAction;
        }
        size = 64;
        default_action = drop;
    }
    apply {

        
        // if (hdr.ipv4.isValid() && hdr.tcp.isValid()){
        //     prev_sketch_calc();
        //     cmp_count_value_register();
        //     percentile_match.apply();
        //     DEBUG_RECORD(0);
        //     DEBUG_RECORD(1);
        //     DEBUG_RECORD(2);
        //     QUANTILE_UPDATE(0);
        //     QUANTILE_UPDATE(1);
        //     QUANTILE_UPDATE(2);

        // }

        forwarding.apply();
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    COUNT_SKETCH_REGISTER(0);
    COUNT_SKETCH_REGISTER(1);
    COUNT_SKETCH_REGISTER(2);

    PREV_TS_SKETCH_REGISTER(0);
    PREV_TS_SKETCH_REGISTER(1);
    PREV_TS_SKETCH_REGISTER(2);
    INGR_TS_SKETCH_REGISTER(0);
    INGR_TS_SKETCH_REGISTER(1);
    INGR_TS_SKETCH_REGISTER(2);
    EGR_TS_SKETCH_REGISTER(0);
    EGR_TS_SKETCH_REGISTER(1);
    EGR_TS_SKETCH_REGISTER(2);
    MAX_GAP_SKETCH_REGISTER(0);
    MAX_GAP_SKETCH_REGISTER(1);
    MAX_GAP_SKETCH_REGISTER(2);
    MIN_GAP_SKETCH_REGISTER(0);
    MIN_GAP_SKETCH_REGISTER(1);
    MIN_GAP_SKETCH_REGISTER(2);

    DEBUG_REGISTER(0);
    DEBUG_REGISTER(1);
    DEBUG_REGISTER(2);

    QUANTILE_REGISTER(0);
    QUANTILE_REGISTER(1);
    QUANTILE_REGISTER(2);
    C_PLUS_SKETCH_REGISTER(0);
    C_PLUS_SKETCH_REGISTER(1);
    C_PLUS_SKETCH_REGISTER(2);
    C_MINUS_SKETCH_REGISTER(0);
    C_MINUS_SKETCH_REGISTER(1);
    C_MINUS_SKETCH_REGISTER(2);



    action add_int_header(){
        hdr.int_hdr.setValid();
        hdr.int_hdr.latency = standard_metadata.egress_global_timestamp - standard_metadata.ingress_global_timestamp;
        hdr.int_hdr.lambda = meta.lambda_value;
        hdr.int_hdr.quantile_value_sketch0 = meta.quantile_value_sketch0;
        hdr.int_hdr.quantile_value_sketch1 = meta.quantile_value_sketch1;
        hdr.int_hdr.quantile_value_sketch2 = meta.quantile_value_sketch2;

        hdr.int_hdr.max_gap_value_sketch0 = meta.max_gap_value_sketch0;
        hdr.int_hdr.min_gap_value_sketch0 = meta.min_gap_value_sketch0;
        hdr.int_hdr.c_minus_value_sketch0 = meta.c_minus_value_sketch0;
        hdr.int_hdr.c_plus_value_sketch0 = meta.c_plus_value_sketch0;
        hdr.int_hdr.count_sketch = meta.count_value_sketch;
        hdr.int_hdr.count_sketch0 = meta.count_value_sketch0;
        hdr.int_hdr.count_sketch1 = meta.count_value_sketch1;
        hdr.int_hdr.count_sketch2 = meta.count_value_sketch2;
        

    }
    

    action prev_sketch_calc(){
        PREV_LAT_TS_RECORD(0, crc16_custom);
        PREV_LAT_TS_RECORD(1, crc16_custom);
        PREV_LAT_TS_RECORD(2, crc16_custom);
    }
    action cmp_count_value_register(){
        meta.count_value_sketch = meta.count_value_sketch0;
        // meta.chosen_idx = 0;
        if(meta.count_value_sketch > meta.count_value_sketch1){
            meta.count_value_sketch = meta.count_value_sketch1;
            // meta.chosen_idx = 1;
        }
        if(meta.count_value_sketch > meta.count_value_sketch2){
            meta.count_value_sketch = meta.count_value_sketch2;
            // meta.chosen_idx = 2;
        }
    }


    action set_percentile_result(bit<16> perc_res){
        if (perc_res < meta.percentile_result || meta.percentile_result == 0){
            meta.percentile_result = perc_res;
        }
    }
    table percentile_match{
        key = {meta.count_value_sketch: range;}
        actions = {set_percentile_result;NoAction;}
        size = 6555;
        default_action = NoAction;  
    }

    apply { 
        //apply sketch
        if (hdr.ipv4.isValid() && hdr.tcp.isValid()){
            prev_sketch_calc();
            meta.latency = hdr.lat.latency;
            cmp_count_value_register();
            percentile_match.apply();
            DEBUG_RECORD(0);
            DEBUG_RECORD(1);
            DEBUG_RECORD(2);
            // if(meta.chosen_idx == 0){
            //     QUANTILE_UPDATE(0);
            // }
            // else if(meta.chosen_idx == 1){
            //     QUANTILE_UPDATE(1);
            // }
            // else if(meta.chosen_idx == 2){
            //     QUANTILE_UPDATE(2);
            // }
            
            
            QUANTILE_UPDATE(0);
            QUANTILE_UPDATE(1);
            QUANTILE_UPDATE(2);
            add_int_header();

        }
     }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

//switch architecture
V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;