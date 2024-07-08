tg_path = ./src/topology_generator.py
p4app_path = ./build/p4app.json

# project_name = intsight
# project_name = lamp
# project_name = mars
# project_name = mars-sketch
project_name = netscope-sketch
# project_name = slot
# project_name = full
# project_name = netscope

int_path = ./src/$(project_name)/p4/main.p4
# gen_args = --output_name $(p4app_path) --p4_path $(int_path) --bw 1000
gen_args = --output_name $(p4app_path) --p4_path $(int_path)

# 实验名
exp ?= experiment
# 实验代码路径
exp_dir ?= global
flag ?= single

ifeq ($(exp),experiment)
	exp_path = ./experiment/experiment.py
else 
	ifeq ($(exp),test)
		exp_path = ./src/$(project_name)/test.py
	else
		ifeq ($(exp),normal)
			exp_path = ./src/$(project_name)/normal.py
		else
			ifeq ($(project_name), netscope-sketch)
				exp_path = ./src/$(project_name)/exp/$(exp).py
			else
				exp_path = ./experiment/exp_$(exp).py
			endif
		endif
	endif
endif

ifeq ($(exp_dir),local)
	exp_path = ./src/$(project_name)/$(exp).py
else
	ifeq ($(exp_dir),eval)
		exp_path = $(exp)
	endif
endif

gen: config
	# python ./src/p4_template.py

	# python $(tg_path) --topo linear -n 5 -d 1 $(gen_args)
	# python $(tg_path) --topo random -n 20 -d 10 $(gen_args)
	python $(tg_path) --topo fat_tree -k 4 $(gen_args)
	# python $(tg_path) --topo spine_leaf -s 2 -l 4  $(gen_args)
	# python $(tg_path) --topo szgd  $(gen_args)
	
	python ./src/add_collector.py
	# rm -f build/entry_handle.json

all: gen run

run: clean clear config
	mkdir log -p
	
	sudo p4run --config ./build/p4app.json --log-dir log/log --pcap-dir log/pcap

rc: 
	sudo python ./src/$(project_name)/routing_controller.py
	mkdir log/hosts -p

clean:
	sudo mn -c
	#p4run --clean

clear: 
	# this will clean all dir whose name contain 'log'
	# p4run --clean-dir
	sudo rm -rf log
	sudo rm -rf pcap
	# sudo rm -rf /mnt/netscope/log
	# sudo rm -rf host_log

exp: 
	sudo rm -rf log/hosts
	mkdir log/hosts
	sudo bash build/receive.sh ${project_name}
	sudo chmod -R a+rw ./log
	nohup sudo python ./src/${project_name}/register_controller.py > log/hosts/receive/s0.log 2>&1 &
	# nohup sudo python ./src/${project_name}/packet/digest.py s0 > log/hosts/receive/s0.log 2>&1 &
	sudo python $(exp_path) $(flag)
	# sudo python ./src/mars/test.py single
	python experiment/batch/draw.py

test: rc exp

init_quantile:
	python ./src/${project_name}/quantile_controller.py --option "set_hashes"

reset_quantile:
	python ./src/${project_name}/quantile_controller.py --option "reset"

get_quantile: 
	# python ./src/${project_name}/quantile_controller.py --option "set_hashes"
	# python ./src/${project_name}/quantile_controller.py --option "reset"
	python ./src/${project_name}/quantile_controller.py --option "decode"  --mod 16


batch: config
	sudo python3 experiment/batch/run_batch.py 

config:
	echo $(project_name) > build/config.txt

web_topo_api:
	python analysis/analysis.py # 故障定位
	python web/topo2html.py     # 生成拓扑html
	python web/service_topo.py  # Flask服务


nohup:
	-rm ./nohup.out
	-ps -ef | grep simple_switch | grep -v grep | cut -c 9-15 | xargs sudo kill -9
	nohup sudo python3 experiment/batch/run_batch.py &

fix: 
	sudo bash -c 'echo "127.0.0.1 $(hostname)" >> /etc/hosts'