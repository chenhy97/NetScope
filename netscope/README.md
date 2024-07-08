## Usage

1. 启动 mininet
    ```shell
    make all
    ```

2. 运行测试（启动背景流量、注入异常）
    - 运行 `experiment/experiment.py` 中 `Experiment` 类的默认实验 `.run()`；
        ```shell
        make test
        ```
    - 运行 `experiment/exp_$(exp).py`
        ```sh
        make test exp=burst
        ```
    - 运行 `src/$(project_name)/test.py`
        ```sh
        make test exp=test
        ```
    - 运行 `src/$(project_name)/$(exp).py`
        ```sh
        make test exp=burst exp_dir=local
        ```
> `project_name` 默认为 `mars`


## Install
### Environment 环境安装

安装 P4 环境
> p4-utils 中的 `install-p4-dev.sh` 中的 `apt install` 部分如遇报错需自行在命令行中运行。

https://github.com/nsg-ethz/p4-utils/tree/master/install-tools

```shell
git clone http://gitlab.dds-sysu.tech/Benature/p4-utils
bash p4-tuils/install-tools/install-p4-dev.sh
```

其他依赖安装（`tcpreplay`, `chaosblade`）：

```shell
bash install.sh
```

### Data Preparing 数据准备

下载[数据集](https://pages.cs.wisc.edu/~tbenson/IMC10_Data.html)，放置在 `/mnt/DataSet` 中。

以 `/mnt/DataSet/univ1` 为例，在其下创建文件夹 `cache`，然后运行

```sh
bash src/src/disposable/tcpprep.sh
```

（`.cache` 文件是 `tcpreplay-edit` 需要用到的文件）


## Fix (in docker)

if encounter like

```
sudo: unable to resolve host xxxxxxxx
```

```sh
sudo bash -c 'echo "127.0.0.1 $(hostname)" >> /etc/hosts'
```



## Others

host_log 数据顺序：先旧后新

```json
"h2": {
        "s2": {
            "delay": null,
            "loss": null,
            "mac": "00:00:0a:02:02:02",
            "intf": "h2-eth0",
            "weight": 1,
            "bw": null,
            "queue_length": null,
            "ip": "10.2.2.2/24"
        },
        "type": "host",
        "gateway": "10.2.2.1",
        "interfaces_to_port": {
            "h2-eth0": 0
        },
        "interfaces_to_node": {
            "h2-eth0": "s2"
        }
    },
```
