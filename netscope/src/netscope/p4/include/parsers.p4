/*************************************************************************
*********************** P A R S E R S  ***********************************
*************************************************************************/

#ifndef __PARSERS__
#define __PARSERS__

#include "defines.p4"
#include "int_headers.p4"

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            TYPE_VLAN: parse_vlan;
            default: accept;
        }
    }

    state parse_vlan {
        packet.extract(hdr.vlan);
        transition select(hdr.vlan.ether_type) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        verify(hdr.ipv4.ihl >= 5, error.IPHeaderTooShort);
        transition select(hdr.ipv4.ihl) {
            5             : detect_ipv4_next;
            default       : parse_ipv4_option;
        }
    }

    state parse_ipv4_option {
        packet.extract(hdr.ipv4_option);
        transition detect_ipv4_next;
    }

    state detect_ipv4_next {
        transition select(hdr.ipv4.protocol) {
            6  : parse_tcp;
            17 : parse_udp;
            default : accept;
        }
    }

    state parse_tcp {
        packet.extract(hdr.tcp);
        meta.src_port = hdr.tcp.src_port;
        meta.dst_port = hdr.tcp.dst_port;
        transition is_ipv4_option_valid;
    }

    state parse_udp {
        packet.extract(hdr.udp);
        meta.src_port = hdr.udp.src_port;
        meta.dst_port = hdr.udp.dst_port;
        transition is_ipv4_option_valid;
    }

    state is_ipv4_option_valid {
        transition select(hdr.ipv4.ihl) {
            5             : accept;
            default       : detect_int;
        }
    }

    state detect_int {
        transition select(hdr.ipv4_option.option){
            IPV4_OPTION_INT: parse_int_shim;
            IPV4_OPTION_NOTICE: verify_debug;
            IPV4_OPTION_INT_REPORT: prepare_report;
            // IPV4_OPTION_INT_REPORT: verify_debug;
            IPV4_OPTION_LATENCY: parse_latency_shim;
            default: accept;
        }
    }

    state parse_int_shim {
        packet.extract(hdr.int_shim);
        transition verify_debug;
    }

    state parse_latency_shim {
        packet.extract(hdr.latency_shim);
        // meta.parser_metadata.latency_count = hdr.ipv4_option.src_count;
        meta.parser_metadata.latency_count = Latency_List_LEN;
        transition select(meta.parser_metadata.latency_count) {
            0 : verify_debug;
            default: parse_latency_loop;
        }
    }
    state parse_latency_loop {
        packet.extract(hdr.latency_data.next);
        meta.parser_metadata.latency_count = meta.parser_metadata.latency_count - 1;
        transition select(meta.parser_metadata.latency_count) {
            0 : verify_debug;
            default: parse_latency_loop;
        }
    }

    // report header
    state prepare_report {
        // transition accept;
        meta.parser_metadata.report_count = hdr.ipv4_option.src_count;
        transition select(meta.parser_metadata.report_count) {
            0 : verify_debug;
            default: parse_report_loop;
        }
    }
    state parse_report_loop {
        // packet.extract(hdr.int_report.next);
        // meta.parser_metadata.report_count = meta.parser_metadata.report_count - 1;
        // transition select(meta.parser_metadata.report_count) {
        //     0 : verify_debug;
        //     default: parse_report_loop;
        // }

        packet.extract(hdr.int_report);
        transition verify_debug;
    }

    // debug header
    state verify_debug {
        transition select(DEBUG){
            true: parse_debug_shim;
            default: accept;
        }
    }
    state parse_debug_shim {
        packet.extract(hdr.debug_shim);
        meta.parser_metadata.debug_count = hdr.debug_shim.count;
        // transition accept;
        transition select(meta.parser_metadata.debug_count) {
            0 : accept;
            default: parse_debug_loop;
        }
    }
    state parse_debug_loop {
        packet.extract(hdr.debug.next);
        meta.parser_metadata.debug_count = meta.parser_metadata.debug_count - 1;
        transition select(meta.parser_metadata.debug_count) {
            0 : accept;
            default: parse_debug_loop;
        }
    }
}

#endif
