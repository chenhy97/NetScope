#!/usr/bin/env python3
from subprocess import Popen
import random
import os
import sys
import re
import shutil
import subprocess
import time
import json
import pandas as pd

if True:
    sys.path.append(os.path.join(os.getcwd(), 'experiment'))
    from experiment import Experiment, INT_TYPE, ROOT_PATH
    sys.path.append(os.getcwd())
    from analysis.load import Loader
    QUEUE_RATE = 200
    # from src.lamp.routing_controller import QUEUE_RATE


def get_EXP_KEY(f):
    EXP_KEY = re.findall(r'^exp_(\w+?)\.py', f)
    EXP_KEY = EXP_KEY[0] if EXP_KEY else f[:-3]
    return EXP_KEY



with open(f"src/{INT_TYPE}/config.json", "r") as f:
    config = json.load(f)
