import json
import os

p4app_path = "./middle/p4app.json"

with open(p4app_path, "r") as f:
    topo_base = json.load(f)


for sw, conf in topo_base['topology']['switches'].items():
    conf['cli_input'] = os.path.join(
        'log/FIB', sw+'.txt')

with open(p4app_path, 'w') as f:
    json.dump(topo_base, f)
