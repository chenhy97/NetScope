clean:
	sudo mn -c
	#p4run --clean

run: clean 
	mkdir log -p
	
	sudo p4run --config ./p4app.json --log-dir log/log --pcap-dir log/pcap