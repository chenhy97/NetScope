#!/bin/bash

INSTALL_DIR=~/install

mkdir -p build/spmf

# prepare for pillow
sudo apt-get install libjpeg-dev zlib1g-dev -y 
# [spmf](https://www.philippe-fournier-viger.com/spmf/) relies on java
sudo apt install default-jdk -y 
sudo apt-get install libssl-dev


function do_tcpreplay {
    tcpreplay_version="4.4.4"
    cd INSTALL_DIR
    wget https://github.com/appneta/tcpreplay/releases/download/v4.4.4/tcpreplay-4.4.4.tar.gz
    tar -zxvf tcpreplay-4.4.4.tar.gz
    rm tcpreplay-4.4.4.tar.gz
    cd tcpreplay-4.4.4

    ./configure 
    make
    sudo make install
}

function do_chaosblade {
    wget https://github.com/chaosblade-io/chaosblade/releases/download/v1.7.0/chaosblade-1.7.0-linux-amd64.tar.gz
    tar -zxvf chaosblade-1.7.0-linux-amd64.tar.gz
    rm chaosblade-1.7.0-linux-amd64.tar.gz
    cd chaosblade-1.7.0
    make
}

function do_golang {
    wget https://go.dev/dl/go1.21.3.linux-amd64.tar.gz
    # sudo rm -rf /usr/local/go && tar -C /usr/local -xzf go1.21.3.linux-amd64.tar.gz
    sudo tar -C /usr/local -xzf go1.21.3.linux-amd64.tar.gz
    echo `export PATH=$PATH:/usr/local/go/bin` >> $HOME/.profile
}

do_tcpreplay
do_chaosblade