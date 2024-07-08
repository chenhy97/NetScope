#ifndef __INT_SOURCE_SINK__
#define __INT_SOURCE_SINK__

// Insert INT header to the packet
control int_source_init (
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata) {

    action int_source() {
        // IPv4 Option
        hdr.ipv4_option.option = IPV4_OPTION_INT; // TODO: flag it is a INT pkt
        // hdr.ipv4_option.src_iCount = 0;
        hdr.ipv4_option.path_id = 0;
        hdr.ipv4_option.abnormal_detected = false;
        
        // insert INT shim header
        hdr.int_shim.setValid();
        hdr.int_shim.src_timestamp = standard_metadata.ingress_global_timestamp;
        hdr.int_shim.qdepth_sum = 0;
        // hdr.int_shim.resv = 0;

        // add the header len (bytes) to total len
        hdr.ipv4.totalLen = hdr.ipv4.totalLen + INT_SHIM_HS;
        hdr.udp.length_ = hdr.udp.length_ + INT_SHIM_HS;

        // hdr.ipv4_option.int_len = 0;
    }

    table tb_int_source {
        key = {
            hdr.ipv4.srcAddr: exact;
        }
        actions = {
            int_source;
            NoAction;
        }
        default_action = NoAction;
    }

    apply {
        tb_int_source.apply();
    }
}

control process_int_sink (
    inout headers hdr,
    inout metadata local_metadata,
    inout standard_metadata_t standard_metadata) {
    // @hidden
    // action restore_header () {
    //     hdr.ipv4.dscp = hdr.intl4_shim.dscp;
    //     // restore length fields of IPv4 header and UDP header
    //     bit<16> len_bytes = ((bit<16>)hdr.intl4_shim.len) << 2;
    //     hdr.ipv4.len = hdr.ipv4.len - len_bytes;
    //     hdr.udp.length_ = hdr.udp.length_ - len_bytes;
    // }

    // @hidden
    action int_sink() {
        // remove all the INT information from the packet
        hdr.int_shim.setInvalid();
        // hdr.int_header.setInvalid();
        // hdr.debug.setInvalid();
        // hdr.debug.pop_front(hdr.debug.size);
        hdr.ipv4.totalLen = hdr.ipv4.totalLen - INT_SHIM_HS;
        hdr.udp.length_ = hdr.udp.length_ - INT_SHIM_HS;
    }

    apply {
        // restore_header();
        // int_sink();
    }
}

control detect_int_source_sink (
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata) {
        action int_set_source () {
            meta.int_meta.source = true;
        }

        action int_set_sink () {
            meta.int_meta.sink = true;
        }

        table tb_set_source {
            key = {
                hdr.ipv4.srcAddr: exact;
            }
            actions = {
                int_set_source;
                NoAction;
            }
            default_action = NoAction;
        }

        table tb_set_sink {
            key = {
                hdr.ipv4.dstAddr: exact;
            }
            actions = {
                int_set_sink;
                NoAction;
            }
            default_action = NoAction;
        }

        apply{
            tb_set_source.apply();
            tb_set_sink.apply();
        }

    }

#endif
