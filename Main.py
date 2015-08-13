__author__ = 'erudhor'


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
from collections import Counter

# Constants
slice_name          = 'budapestple_cloud'
rsa_file            = 'ssh_needs/id_rsa'
knownHosts_file     = 'ssh_needs/known_hosts'
# target ip
traceroute_skeleton = "traceroute -w 5.0 -q 3 %s"

# ip address - time - interval - bandwidth Mbitps - port
iperf_client_skeleton      = "iperf -c %s -u -t %d -i %d -b %dm -f m -p %d"

# ip(interface), port
iperf_server_skeleton = 'iperf -s -B %s -u -p %d'

used_procs   = 10
used_threads = 10

RUN_MEASURES = ["iperf"]#, "traceroute"]


target1 = "152.66.244.82"
target2 = "152.66.127.81"
target_names = [target1, target2]
target_username = "mptcp"

nodes = []
measures = []
results = []


Connection.connectionbuilder =\
    ConnectionBuilder(slice_name, rsa_file, None)

import logging
class MyFilter(logging.Filter):
    def filter(self, record):

        return "paramiko" not in record.name

logger = paramiko.util.logging.getLogger()#logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
        '[%(asctime)s][%(name)s] %(message)s', datefmt='%M.%S')
handler.setFormatter(formatter)
handler.addFilter(MyFilter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def main():
    logger.info("Program started")

    measure_iperf_3()

    logger.info("Saving results")
    persist()
    logger.info("Program ened")
    exit()

    init()
    measure()
    persist()

def start_server(target):
    print "Starting iperf server on: ", target["name"]
    stdout, stderr = target["connection"].runCommand(target["start_command"], timeout=None)
    target["stdout"] = stdout
    target["stderr"] = stderr
    print "Iperf server on %s ended." % target["name"]

    print "Checking for error..."
    if len(stderr) > 0:
        print "Errors found:"
        print stderr

    print "Normal output:"
    print stdout


def measure_iperf_3():
    port = 5200
    duration = 6
    node_names = bestNodes()[:1]
    nodes = []

    logger.info("Initializing iperf measures")
    for node_name in node_names:
        measure = ParalellMeasure()
        measure1 = IperfMeasure(node_name, target_names[0], target_username, port, duration)
        measure2 = IperfMeasure(node_name, target_names[1], target_username, port, duration)
        measure.addMeasure(measure1, 0)
        measure.addMeasure(measure2, 3)
        nodes.append(measure)

    for node in nodes:
        node.startMeasure()
        node.join()
        print node.getData()

def measure_iperf_2():
    port = 5200
    duration = 3
    node_names = bestNodes()[:1]
    nodes = []

    logger.info("Initializing iperf measures")
    for node_name in node_names:
        measure = IperfMeasure(node_name, target_names[0], target_username, port)
        nodes.append(measure)
        measure = IperfMeasure(node_name, target_names[1], target_username, port)
        nodes.append(measure)

    logger.info("Running measures")
    for node in nodes:
        node.runIperf(duration)
        measures.append(node)


def measure_iperf():
    global target_names
    node_names = ["194.29.178.14"]
    port = 5200
    targets = []
    target = None
    print "Test started"
    #try:
    for target_name in target_names:
        target = {
            "name": target_name,
            "connection": Connection
            (target_name, target_username)
        }
        target["connection"].connect()
        print "Connected to target: ", target_name
        targets.append(target)
    #except:
    #    print "Error at connecting to target server: ", target
    #    print traceback.format_exc()
    #    exit()

    for target in targets:
        target["start_command"] = iperf_server_skeleton %\
                                  (target["name"], port)
        t = threading.Thread(target=start_server, args=(target, ))
        t.start()
        target["thread"] = t

    sleep(1)
    print "Starting clients:"
    node_names = bestNodes()[0:1]
    nodes = []
    try:
        for node_name in node_names:
            node = {
                "name": node_name,
                "connection": Connection(node_name)
            }
            print "Connected to node: ", node_name
            nodes.append(node)
    except:
        print "Error at connecting to node: ", target

    print "Connections built to nodes."

    for node in nodes:
        node["iperf_installation"] = check_iperf(node["name"])
        print node["iperf_installation"]
        if "installed" not in node["iperf_installation"]:
            continue
        print "Starting iperf client on: ", node["name"]
        # ip address - time - interval - bandwidth Mbitps - port
        cmd = iperf_client_skeleton %\
              (targets[0]["name"], 10, 1, 100, port)
        stdout, stderr = node["connection"].\
            runCommand(cmd, timeout=15)
        node["stdout"] = stdout
        node["stderr"] = stderr
        print "Iperf server on %s ended." % node["name"]

        print "Checking for error..."
        if len(stderr) > 0:
            print "Errors found:"
            print stderr

        print "Normal output:"
        print stdout

    print "Close servers"
    for target in targets:
        target["connection"].disconnect()
    print "Test ended"


    # Start iperf client on node and get results


def init():
    global measures, target_names, nodes

    #nodes = getPlanetLabNodes(slice_name)
    nodes = bestNodes()
    print "number of nodes: ", len(nodes)
    print "\tfirst node: ", nodes[0]

    # Build up the needed Measures
    for target in target_names:
        for node in nodes:#nodes[200:300]:
            measures.append(TracerouteMeasure(node, target))


def persist():
    global results

    for measure in measures:
        data = measure.getData()
        if data is not None:
            results.append(data)

    if len(results) == 0:
        return

    timeStamp = getTime().replace(":", ".")[0:-3] # escape : to . and remove seconds
    filename = 'results/rawTrace_%s_%s.txt'%(getDate(), timeStamp)
    with open(filename,'w') as f:
        f.write(json.dumps(results, indent=2))

    """
    filename = 'results/rawTrace_%s_%s.txt.gzip'%(getDate(), timeStamp)
    with open(filename,'w') as f:
        blob        = json.dumps(results, indent=2)
        blob_gzip   = zlib.compress(blob, 9)
        blob_base64 = base64.b64encode(blob_gzip)
        f.write(blob_base64)
    """


def measure():
    global measures

    def connectAndMeasure(measure):
        connected = measure.connect()
        if connected:
            measure.runMeasure()
        return measure

    begin = time()
    print "runMeasurements on %d threads..."%used_threads
    measures = thread_map(connectAndMeasure, measures, used_threads)
    #workers = Pool(used_threads)
    #measures2 = workers.map(connectAndMeasure, measures)
    print "Elapsed time: %0.0f seconds"% (time() - begin)
    suceed = reduce(
        lambda acc, new:
            acc+1 if new.error == None else acc,
        measures, 0)
    print "Succeed measures: %d"%suceed


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
    print "Install node: ", ip
    cmd_install = "sudo yum install -y iperf"
    con.runCommand(cmd_install, timeout=25)


def check_iperf(node):
    cmd_install = "sudo yum install -y iperf"
    cmd_test = "iperf -v"
    not_installed_test = "iperf: command not found"
    installed_test = "iperf version"

    print "Check node: ", node

    if not ping(node):
        return "offline"

    try:
        con = connBuilder.getConnection(node)
    except Exception:
        return "connection fail"

    try:
        err, outp = con.runCommand(cmd_test)
    except Exception:
        return "runtime error"

    if len(err) > 0:
        return "runtime error"

    if installed_test in outp:
        version = outp.split(" ")[2]
        return "installed - version: %s" % version

    if not_installed_test not in outp:
        return "installation abbandoned: " + outp

    try:
        install_iperf(con, node)
    except Exception:
        return "install failed: "+\
               traceback.format_exc().splitlines()[-1]

    try:
        err, outp = con.runCommand(cmd_test)
    except Exception:
        return "install failed: "+\
               traceback.format_exc().splitlines()[-1]

    if len(err) > 0:
        return "install failed: "+ err.splitlines()[-2:-1]

    if installed_test in outp:
        version = outp.split(" ")[2]
        return "freshly installed - version: %s" % version

    return "install failed: "+outp


def inception(nodes):
    return thread_map(check_iperf, nodes, used_threads)


def testOs(node_ip):
    cmd = "cat /etc/issue"
    node = {"ip": node_ip}
    online = ping(node["ip"])
    node["online"] = online
    if not online:
        return node

    try:
        con = connBuilder.getConnection(node["ip"])
    except Exception:
        error_lines = traceback.format_exc().splitlines()
        node["error"] = error_lines[-1]
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

    print "start scanning on %d threads" % (used_threads*used_procs)
    # results = thread_map(install_iperf, nodes, used_threads)
    # results = proc_map(install_iperf, nodes, used_threads)

    node_lists   = splitList(nodes, int(len(nodes)/used_procs))
    result_lists = proc_map(inception, node_lists, used_procs)
    results      = glueList(result_lists)

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
                        acc+1 if new["online"] else acc,
                    nodes, 0)
    print "Online nodes: ", online

    error = reduce(lambda acc, new:
                    acc+1 if new.has_key("error") else acc,
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

        #print "==============================="
        #print errors
        #print "==============================="
        #print outp


def splitList(list, splitLen):
    splitted_list = []
    i = 0
    j = 0
    split = []
    for node in list:
        split.append(node)
        if (j) % (splitLen) == splitLen-1:
            splitted_list.append(split)
            split = []
            i += 1
        j += 1

    splitted_list.append(split)

    return splitted_list


def glueList(list_of_lists):
    results = []
    for list in list_of_lists:
        results.extend(list)
    return results


if __name__ == "__main__":
    main()
