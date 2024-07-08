/*************************************************************************
*********************** D E F I N E S  ***********************************
*************************************************************************/

#ifndef __DEFINES__
#define __DEFINES__

const bit<8>  UDP_PROTOCOL = 0x11;
const bit<16> TYPE_IPV4 = 0x0800;
const bit<16> TYPE_VLAN = 0x8100;


const bit<5>  IPV4_OPTION_INT = 31;
const bit<5>  IPV4_OPTION_INT_REPORT = 29;
const bit<5>  IPV4_OPTION_LATENCY = 28;
const bit<5>  IPV4_OPTION_NOTICE = 27;


#define MAX_HOPS 9

// Latency Report Buffer
#define Latency_List_LEN 8
// typedef bit<6> flow_id_t; // 2^6=64
// #define FLOW_ID_SIZE 64 // bit<6>


// Clone
const bit<32> E2E_CLONE_SESSION_ID = 2;
// const bit<32> I2E_CLONE_SESSION_ID = 3;

#define PKT_INSTANCE_TYPE_NORMAL 0
#define PKT_INSTANCE_TYPE_INGRESS_CLONE 1
#define PKT_INSTANCE_TYPE_EGRESS_CLONE 2
#define PKT_INSTANCE_TYPE_COALESCED 3
#define PKT_INSTANCE_TYPE_INGRESS_RECIRC 4
#define PKT_INSTANCE_TYPE_REPLICATION 5
#define PKT_INSTANCE_TYPE_RESUBMIT 6


#define DEBUG true
// #define DEBUG false
// be careful of report header parsing

#endif