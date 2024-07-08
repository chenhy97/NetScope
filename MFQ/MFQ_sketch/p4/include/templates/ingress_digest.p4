if (hdr.int_report[${idx}].isValid()) {
    meta.D.report.index = hdr.int_report[${idx}].index;
    meta.D.report.src_ip = hdr.int_report[${idx}].src_ip;
    meta.D.report.dst_ip = hdr.int_report[${idx}].dst_ip;
    meta.D.report.epoch_ingress_timestamp = hdr.int_report[${idx}].epoch_ingress_timestamp;
    meta.D.report.latency = hdr.int_report[${idx}].latency;
    meta.D.report.path_pkt_size = hdr.int_report[${idx}].path_pkt_size;
    // meta.D.report.qdepth_sum = hdr.int_report.qdepth_sum;
    // meta.D.report.path_count = hdr.int_report.path_count;
    meta.D.report.qdepth_sum_AND_path_count = hdr.int_report[${idx}].qdepth_sum ++ hdr.int_report[${idx}].path_count;
    // meta.D.report.flow_count = hdr.int_report.flow_count;
    // meta.D.report.flow_drop = hdr.int_report.flow_drop;
    meta.D.report.flow_count_AND_drop = hdr.int_report[${idx}].flow_count ++ hdr.int_report[${idx}].flow_drop;
    meta.D.report.path_id = (bit<8>)hdr.int_report[${idx}].path_id;

    digest<report_digest_t>(1, meta.D.report);
}