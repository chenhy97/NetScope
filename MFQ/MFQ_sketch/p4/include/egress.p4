#ifndef __EGRESS__
#define __EGRESS__

// control egress_clone (
//     inout headers hdr,
//     inout metadata meta,
//     inout standard_metadata_t standard_metadata) {

//     action send_collector(ip4Addr_t ip4DstAddr, macAddr_t macDstAddr) {
//         // change destination
//         // hdr.ethernet.dstAddr = macDstAddr;
//         hdr.ipv4.dstAddr = ip4DstAddr;
//     }

//     table collector_header{
//         key = {}
//         actions = {
//             send_collector;
//             NoAction;
//         }
//         default_action = NoAction;
//     }

//     apply {

//     }
// }




#endif