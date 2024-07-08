import json
from topology_generator import SW_CONF

p4app_path = "./build/p4app.json"

with open(p4app_path, "r") as f:
    topo_base = json.load(f)


def add_collector():
    for sw in topo_base['topology']['switches']:
        topo_base['topology']['links'].append(["s0", sw])

    topo_base['topology']['hosts']['h0'] = {}
    topo_base['topology']['switches']['s0'] = SW_CONF
    topo_base['topology']['links'].append(["h0", "s0"])
    return topo_base


def gen_receive_sh(topo_base):
    receive_dir = 'log/hosts/receive'
    digeset_dir = 'log/hosts/digest'

    content = f"mkdir -p {receive_dir}\n"
    for h in topo_base['topology']['hosts'].keys():
        content += f"nohup sudo mx {h} ./src/$1/packet/receive.py {h}-eth0 > {receive_dir}/{h}.log 2>&1 &\n"

    content += "\n"

    content += f"mkdir -p {digeset_dir}\n"
    for sw in topo_base['topology']['switches'].keys():
        # if sw == "s0": continue
        content += f"nohup sudo python ./src/$1/packet/digest.py {sw} > {digeset_dir}/{sw}.log 2>&1 &\n"

    with open("build/receive.sh", 'w') as f:
        f.write(content)


if __name__ == "__main__":
    topo_base = add_collector()
    with open(p4app_path, 'w') as f:
        json.dump(topo_base, f)
    gen_receive_sh(topo_base)
