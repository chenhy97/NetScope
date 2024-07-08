import os
import re
from string import Template

LOOP_SIZE = 1


with open('build/config.txt', 'r') as f:
    INT_TYPE = f.read().strip('\n')
    print("INT_TYPE:", INT_TYPE)

p4_dir = os.path.join('src', INT_TYPE, 'p4')
template_dir = os.path.join(p4_dir, 'include/templates')
render_dir = os.path.join(p4_dir, 'include/render')

with open(os.path.join(p4_dir, 'int.p4'), 'r') as f:
    main_p4 = f.read()
    buffer_size = re.findall(r"\n\#define BUFFER_SIZE (\d+)", main_p4)
    buffer_size = int(buffer_size[0])


for fn in os.listdir(template_dir):
    if not fn.endswith(".p4"):
        continue

    with open(os.path.join(template_dir, fn), 'r') as f:
        p4file = f.read()
        if p4file.strip() == "":
            continue
        s = Template(p4file)
    print(f"Rendering file: {fn}")
    content = f"// Total Loop Size: {LOOP_SIZE}\n\n"
    for i in range(LOOP_SIZE):
        content += f"// ====== LOOP INDEX {i} =======\n"
        content += s.substitute({'idx': i}) + "\n\n"

    with open(os.path.join(render_dir, fn), 'w') as f:
        f.write(content)
