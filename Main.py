__author__ = 'erudhor'


from RemoteScripting import *
from Measuring import *
from time import time
from datetime import date, datetime
import sys
sys.path.append("utils")
import trparse
from threadedMap import conc_map
import json
from multiprocessing import Pool
import zlib
import base64
import paramiko

# Constants
slice_name          = 'budapestple_cloud'
rsa_file            = 'ssh_needs/id_rsa'
knownHosts_file     = 'ssh_needs/known_hosts'
traceroute_skeleton = "traceroute -w 5.0 -q 3 %s"
iperf_skeleton      = "iperf -c %s -u"
used_threads        = 3


host1 = "152.66.244.83"#Official
host2 = "152.66.127.83"#Test
targets = [host1, host2]

nodes = []
measures = []
results = []

connBuilder = ConnectionBuilder(slice_name, rsa_file, None)
TracerouteMeasure.connection_builder = connBuilder


def main():
    init()
    test()

    exit()
    init()
    measure()
    persist()


def test():
    global targets
    target = "128.208.4.198"#"planetlab1.tmit.bme.hu"
    targets = [target]
    port = 5200
    # Start iperf server on target
    server_script = 'nohup iperf -s -u -p %d >> iperf_server.out'%port
    targetConnection = None

    try:
        targetConnection = connBuilder.getConnection(target)
    except:
        print "Error at connecting to target: ", target
        print traceback.format_exc()
        exit()

    output, errors = targetConnection.runCommand(server_script)

    if len(errors) > 0:
        print "Error at starting remote iperf server:"
        for line in errors.readLines():
            print line
        exit()

    print "Output:"
    for line in output.readLines():
        print line


    # Start iperf client on node and get results

def persist():
    global results

    for measure in measures:
        results.append(measure.getData(sendError=False))

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

def init():
    global measures, targets, nodes

    #nodes = getPlanetLabNodes(slice_name)
    #nodes = ["pli1-pa-1.hpl.hp.com"]
    nodes = bestNodes()[0:5]
    targets = ["152.66.244.83"]
    print "number of nodes: ", len(nodes)
    print "\tfirst node: ", nodes[0]

    # Build up the needed Measures
    for target in targets:
        for node in nodes:#nodes[200:300]:
            measures.append(TracerouteMeasure(node, target))

def measure():
    global measures

    def connectAndMeasure(measure):
        connected = measure.connect()
        if connected:
            measure.runMeasure()
        return measure

    begin = time()
    print "runMeasurements on %d threads..."%used_threads
    measures = conc_map(connectAndMeasure, measures, used_threads)
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

if __name__ == "__main__":
    main()
