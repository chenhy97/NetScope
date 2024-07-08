import requests
import os
import sys
import json
import subprocess

MININET_READY = False


def wechat_bot(message):
    api = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=9a41bc20-dd0c-4a26-82d9-0f9d8c00a624'
    headers = {"Content-Type": "text/plain"}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": message,
            "mentioned_list": ["@all"],
            "mentioned_mobile_list": ["@all"],
        }
    }
    r = requests.post(api, headers=headers, json=data)


def kill_p(name):
    '''kill process'''

    for i in range(2):
        ps = subprocess.Popen(f"ps -eaf | grep {name}",
                              shell=True,
                              stdout=subprocess.PIPE)
        ps.wait()
        output = str(ps.stdout.read())[2:-1].replace('\\n', '\n')
        if output.count('\n') > 2:
            print(f"killing {name}")
            subprocess.Popen(
                f'ps -ef | grep {name} | grep -v grep | cut -c 9-15 | xargs sudo kill -9',
                shell=True).wait()
        else:
            if i == 0:
                print(f"No {name} process was found.")


def start_mininet():
    global MININET_READY
    MININET_READY = False
    log_cotent = ""
    # make run
    kill_p("simple_switch")
    run_p = subprocess.Popen(['make', 'run'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    for i, l in enumerate(iter(run_p.stdout.readline, b'')):
        line = l.decode()
        if '[1;44mINFO' in line or line == '':
            continue
        log_cotent += line
        if i % 10 == 0:
            print('', end='.')
            sys.stdout.flush()
        if '*** Starting CLI:' in line:
            print('Mininet Started!')
            with open('log/make.log', 'w') as f:
                f.write(log_cotent)
            MININET_READY = True
            return run_p
            break
    print("Fail to Start mininet")
    sys.exit(-1)
    return None


batch_num = 10

if __name__ == "__main__":
    exp_config = {
        # 'ad_both_none': batch_num,
        # 'ad_both': batch_num,
        'ad_long': batch_num,
        'ad_short': batch_num,
        'ad_long_none': batch_num,
        'ad_short_none': batch_num,
        # 'burst': 30,
        # 'ecmp_imbalance': 30,
        # "drop_link": 60,
        # 'delay': 60,
        # 'port_queue': 30,
    }
    for exp, exp_count in exp_config.items():
        for ti in range(exp_count):
            exp_info_string = f"EXPERIMENT {exp} {ti+1}/{exp_count}"
            print(
                f"{'='*len(exp_info_string)}\n{exp_info_string}\n{'='*len(exp_info_string)}"
            )

            p_mn = start_mininet()
            print(p_mn)

            if p_mn is None or MININET_READY == False:
                sys.exit(-1)

            with open('./log/rc.log', 'w') as f:
                # make rc
                subprocess.Popen(['make', 'rc'], stdout=f, stderr=f).wait()

            # make exp exp={exp}
            print(p_mn)
            subprocess.Popen(['make', 'exp', f'exp={exp}',
                              'flag=batch']).wait()

            p_mn.kill()

            # with open('./build/build.json', 'r') as f:
            #     build = json.load(f)

            # python3 analysis/analysis.py --data_path xxx
            # subprocess.Popen([
            #     'python3', 'analysis/analysis.py', '--data_path',
            #     build['data_path'], '-l', '1'
            # ]).wait()

            print('\n\nend exp now!\n\n')
        if exp_count:
            wechat_bot(exp + ' finish')
    wechat_bot('batch finish')
