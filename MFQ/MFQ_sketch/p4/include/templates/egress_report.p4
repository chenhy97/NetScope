
// Note: be care of I/O comflict (atomic)
// buffer_index_reg.read(meta.recir_index, Recirculate_I);
buffer_src_tstamp.read(epoch_ingress_timestamp, meta.recir_index);

// re-use: whether recir is end
// hdr.ipv4_option.abnormal_detected = true;

// ingress timestamp is 0 means that this buffer is empty
if (epoch_ingress_timestamp != 0) { 
    hdr.debug[0].state = 1;

    { // header
        hdr.ipv4_option.src_count = 0;

        if (!hdr.int_report[${idx}].isValid()) {
            // hdr.int_report.push_front(1);
            hdr.int_report[0].setValid();
        }

        hdr.ipv4_option.src_count = hdr.ipv4_option.src_count + 1;
        hdr.udp.length_ = hdr.udp.length_ + (bit<16>)INT_REPORT_HS;
        hdr.ipv4.totalLen = hdr.ipv4.totalLen + (bit<16>)INT_REPORT_HS;
        
        // load data to header
        hdr.int_report[0].index = (bit<8>) meta.recir_index;
        buffer_src_ip.read(hdr.int_report[0].src_ip, meta.recir_index);
        buffer_dst_ip.read(hdr.int_report[0].dst_ip, meta.recir_index);
        hdr.int_report[0].epoch_ingress_timestamp = epoch_ingress_timestamp;
        buffer_latency.read(hdr.int_report[0].latency, meta.recir_index);
        buffer_qdepth.read(hdr.int_report[0].qdepth_sum, meta.recir_index);
        buffer_path_count.read(hdr.int_report[0].path_count, meta.recir_index);
        buffer_flow_count.read(hdr.int_report[0].flow_count, meta.recir_index);
        buffer_flow_drop.read(hdr.int_report[0].flow_drop, meta.recir_index);
        buffer_path_id.read(hdr.int_report[0].path_id, meta.recir_index);
        buffer_path_pkt_size.read(hdr.int_report[0].path_pkt_size, meta.recir_index);
    }
    
    // reset tstamp to 0, flag the buffer to be empty
    buffer_src_tstamp.write(meta.recir_index, 0);                    

    // update recir index, point to next buffer
    meta.recir_index = (meta.recir_index + 1) % (BUFFER_SIZE);

    // buffer_index_reg.write(Recirculate_I, meta.recir_index);

    // // debug
    // recirculate(standard_metadata);
    // // mark_to_drop(standard_metadata);
}
