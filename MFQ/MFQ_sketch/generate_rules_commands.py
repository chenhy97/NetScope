import numpy as np
command_str = "table_add percentile_match set_percentile_result {}->{} => {} 0"
print(command_str.format(0,5,0))
for i in range(5, 2**16 - 1, 10):
    start = i+1
    end = i + 10
    idx = int(np.ceil(i/10))
    print(command_str.format(start, end, idx))

# import numpy as np
# phi = 0.1
# perc_range = {}
# for i in range(1, 10000):
#     perc_res = round(i-i*phi)
#     if perc_res not in perc_range.keys():
#         perc_range[perc_res] = []
#     perc_range[perc_res].append(i)
# command_str = "table_add percentile_match set_percentile_result {}->{} => {} 0"
# for key, range in perc_range.items():
#     start = range[0]
#     end = range[-1]
#     idx = key
#     print(command_str.format(start, end, idx))