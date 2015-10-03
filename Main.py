__author__ = 'Rudolf Horvath'

import sys

sys.path.append("utils")
from RemoteScripting import *
from Measuring import *
import json
import paramiko
import os
import subprocess
import logging
import traceback

# Constants
rsa_file = 'ssh_needs/id_rsa'
knownHosts_file = 'ssh_needs/known_hosts'

used_procs = 100
used_threads = 200

RUN_MEASURES = ["iperf"]  # , "traceroute"]

target1 = "152.66.244.82"
target2 = "152.66.127.81"
target_names = [target1, target2]
target_username = "mptcp"

Connection.connectionbuilder = \
    ConnectionBuilder(slice_name, rsa_file, None)

logger = logging.getLogger()


def main():
    continous_measuring()


def setup_logging():
    global logger

    class MyFilter(logging.Filter):
        def filter(self, record):
            keywords = ["paramiko", "requests", "urllib3"]
            return all(map(lambda x: x not in record.name, keywords))
            # return "paramiko" not in record.name and "requests" not in record.name and "urllib3" not in record.name

    logger = paramiko.util.logging.getLogger()  # logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s][%(name)s] %(message)s', datefmt='%M.%S')
    handler.setFormatter(formatter)
    handler.addFilter(MyFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def saveOneMeasure(data):
    timeStamp = getTime().replace(":", ".")[0:-3]
    filename = 'results/%s/%s/rawTrace_%s_%s.json' % (getDate(), timeStamp[:2], getDate(), timeStamp)

    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    with open(filename, 'w') as f:
        f.write(json.dumps(data, indent=2))


def continous_measuring():

    def measure_node(node, i):
        log = "empty string"
        try:
            log = subprocess.check_output(["python", "SingleMeasure.py", "-n", node])
        except Exception:
            log = "Reaching node %s failed:\n%s" % (node, traceback.format_exc())

        # Save log for last measure
        with open("Main.py.%d.log" % i, 'w') as f:
            f.write(log)

    while True:
        nodes = getPlanetLabNodes(slice_name)
        i = 0
        for node in nodes:
            i = (i+1)%5
            measure_node(node, i)


if __name__ == "__main__":
    main()