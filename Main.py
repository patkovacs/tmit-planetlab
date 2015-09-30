__author__ = 'Rudolf Horvath'

import sys

sys.path.append("utils")
from RemoteScripting import *
from Measuring import *
from time import time, sleep
from datetime import date, datetime
import trparse
from threadedMap import thread_map, proc_map
import json
import threading
from multiprocessing import Pool
import zlib
import base64
import paramiko
import os
from collections import Counter
import subprocess
import logging

# Constants
slice_name = 'budapestple_cloud'
rsa_file = 'ssh_needs/id_rsa'
knownHosts_file = 'ssh_needs/known_hosts'
# target ip
traceroute_skeleton = "traceroute -w 5.0 -q 3 %s"

# ip address - time - interval - bandwidth Mbitps - port
iperf_client_skeleton = "iperf -c %s -u -t %d -i %d -b %dm -f m -p %d"

# ip(interface), port
iperf_server_skeleton = 'iperf -s -B %s -u -p %d'

used_procs = 100
used_threads = 200

RUN_MEASURES = ["iperf"]  # , "traceroute"]

target1 = "152.66.244.82"
target2 = "152.66.127.81"
target_names = [target1, target2]
target_username = "mptcp"

nodes = []
measures = []
results = []

Connection.connectionbuilder = \
    ConnectionBuilder(slice_name, rsa_file, None)

logger = logging.getLogger()


def main():
    #continous_measuring()
    scan_os_types()
    get_scan_statistic()


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


def bestNodes():
    return ["128.208.4.198",
            "194.29.178.14",
            "195.113.161.84",
            "204.123.28.51",
            "193.63.75.20",
            "147.83.30.166",
            "130.104.72.213",
            "72.36.112.71",
            "159.217.144.110",
            "131.247.2.242",
            "138.246.253.3",
            "132.239.17.226",
            "194.29.178.13",
            "141.20.103.211",
            "200.19.159.34",
            "206.117.37.5",
            "142.103.2.2",
            "203.178.133.2",
            "193.137.173.218",
            "141.22.213.34",
            "195.113.161.13",
            "195.148.124.73",
            "138.246.253.1",
            "198.82.160.239",
            "130.192.157.131",
            "131.188.44.100",
            "193.136.19.29",
            "128.232.103.203",
            "128.112.139.97",
            "128.232.103.202",
            ]


def install_iperf(con, ip):
    cmd_install = "sudo yum install -y iperf"
    con.runCommand(cmd_install, timeout=25)


def check_iperf(node):
    log = logger.getChild(str(node).replace(".", "_") + ".checkIperf").info
    # cmd_install = "sudo yum install -y iperf"
    cmd_test = "iperf -v"
    not_installed_test = "iperf: command not found"
    installed_test = "iperf version"

    log("Check node: " + node)

    if not ping(node):
        log("offline")
        return "offline"

    try:
        con = Connection(node)
        con.connect()
        if con.errorTrace is not None:
            log("Error at connection: " + con.errorTrace)
    except Exception:
        log("Error at connection: " + traceback.format_exc())
        return "connection fail"

    try:
        err, outp = con.runCommand(cmd_test)
    except Exception:
        log("Error at remote execution: " + traceback.format_exc())
        return "runtime error"

    if len(err) > 0:
        log("Runtime error at remote execution: " + err)
        return "runtime error"

    if installed_test in outp:
        version = outp.split(" ")[2]
        log("installed version: " + version)
        return "installed - version: %s" % version

    if not_installed_test not in outp:
        log("Installation not possible: " + outp)
        return "installation abbandoned: " + outp

    log("Installation started")
    try:
        install_iperf(con, node)
    except Exception:
        log("Installation failed: " + traceback.format_exc())
        return "install failed: " + \
               traceback.format_exc().splitlines()[-1]

    try:
        err, outp = con.runCommand(cmd_test)
    except Exception:
        log("Installation failed: " + traceback.format_exc())
        return "install failed: " + \
               traceback.format_exc().splitlines()[-1]

    if len(err) > 0:
        log("Installation failed: " + err)
        return "install failed: " + err.splitlines()[-2:-1]

    if installed_test in outp:
        version = outp.split(" ")[2]
        log("Installation suceed, new version: " + version)
        return "freshly installed - version: %s" % version

    log("Installation failed: " + outp)
    return "install failed: " + outp


def testOs(node_ip):
    cmd = "cat /etc/issue"
    # uname -r --> gives some more inforamtion about kernel and architecture
    node = {"ip": node_ip}

    con = Connection(node["ip"])
    con.connect()

    node["online"] = con.online

    if con.error is not None:
        node["error"] = con.errorTrace.splitlines()[-1]
        return node

    try:
        outp, err = con.runCommand(cmd)
    except Exception:
        error_lines = traceback.format_exc().splitlines()
        node["error"] = error_lines[-1]
        return node

    if len(err) > 0:
        node["error"] = err
        return node

    node["outp"] = outp

    if "Fedora" in outp or "CentOS" in outp:
        node["os"] = outp.split("\n")[0]

    return node


def scan_iperf_installations():
    print "get node list"
    nodes = getPlanetLabNodes(slice_name)

    print "start scanning on %d threads" % (used_threads * used_procs)
    results = thread_map(install_iperf, nodes, used_threads)
    # results = proc_map(install_iperf, nodes, used_threads)

    print "--------------------"
    c = Counter(results)
    print "Results:"

    stats = {"date": getDate(), "time": getTime()}
    for item in c.most_common():
        stats[item[0]] = item[1]

    print json.dumps(stats, indent=2)

    with open("results/installations.json", "w") as f:
        f.write(json.dumps(stats, indent=2))


def scan_os_types():
    print "get planet lab ip list"
    node_ips = getPlanetLabNodes(slice_name)

    print "start scanning them "
    nodes = thread_map(testOs, node_ips, used_threads)

    print "write out the results"
    with open("results/scan.json", "w") as f:
        f.write(json.dumps(nodes))

    print "create statistics"
    online = reduce(lambda acc, new:
                    acc + 1 if new["online"] else acc,
                    nodes, 0)
    print "Online nodes: ", online

    error = reduce(lambda acc, new:
                   acc + 1 if new.has_key("error") else acc,
                   nodes, 0)
    print "Occured errors: ", error


def get_scan_statistic():
    with open("results/scan.json", "r") as f:
        nodes = json.loads(f.read())
        errors = Counter()
        outp = Counter()
        offline = 0
        for node in nodes:
            if not node["online"]:
                offline += 1
                continue
            if node.has_key("error"):
                errors[node["error"]] += 1
            else:
                outp[node["outp"]] += 1

        print "Offline count: ", offline, "\n"

        for type, count in errors.most_common(len(errors)):
            print "Error count:%d\n\t%s" % (count, type)

        for type, count in outp.most_common(len(outp)):
            print "Output count:%d\n\t%s" % (count, type)

            # print "==============================="
            # print errors
            # print "==============================="
            # print outp


if __name__ == "__main__":
    main()
