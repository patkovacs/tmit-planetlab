__author__ = 'Rudolf Horvath'
__date__ = "2015.06.15"

from RemoteScripting import *
from time import time
from datetime import date, datetime
import trparse
import json
from multiprocessing import Pool

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

def test():
    connBuilder = ConnectionBuilder(slice_name, rsa_file, None)
    TracerouteMeasure.connection_builder = connBuilder
    target = "152.66.244.83"
    node = "pli1-pa-1.hpl.hp.com"
    measure = TracerouteMeasure(node, target)

    print "connecting"
    succeed = measure.connect()
    if succeed:
        print "connected"
        print "measure started"
        succeed = measure.runMeasure()
        print "measure ended"
        if succeed:
            print "measure succeed"
            print "result:"
            print measure.rawResult
        else:
            print "measure unsuccessful"
            print "error: ", measure.error
            print "Trace:\n", measure.errorTrace
    else:
        print "connection failure"
        print "error: ", measure.error
        print "Trace:\n", measure.errorTrace

def persist():
    global results

    for measure in measures:
        results.append(measure.getData())

    timeStamp = getTime().replace(":", ".")[0:-3] # escape : to . and remove seconds
    filename = 'results/rawTrace_%s_%s.txt'%(getDate(), timeStamp)
    with open(filename,'w') as f:
        f.write(json.dumps(results, indent=2))

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


def connectAndMeasure(measure):
    connected = measure.connect()
    if connected:
        measure.runMeasure()
    return measure


def measure():
    global measures
    workers = Pool(used_threads)
    begin = time()
    print "runMeasurements on %d threads..."%used_threads
    measures = workers.map(connectAndMeasure, measures)
    print "Elapsed time: %0.0f seconds"% (time() - begin)
    #suceed = reduce(lambda bool: )

def measure_old():
    connected = 0
    success = 0
    begin = last = time()
    tried = 0
    offline = 0
    # Run them once at a time
    for measure in measures:
        tried += 1
        succeed = measure.connect()
        if succeed:
            connected += 1
            print " - connected (",connected,")\t[tried: ", tried, "]"
            measure.runMeasure()
            if measure.error == None:
                success += 1
                print " + succeed (", success, ")"
                print " - elapsed time: %0.0f seconds"% (time() - begin)
                print " - measure time: %0.0f seconds"% (time() - last)
        else:
            print "offline - ", measure.fromIP
            offline += 1
        last = time()

    print "tried: ", len(measures)
    print "connected: ", connected
    print "succeed: ", success
    print "offline: ", offline

def main():
    init()
    measure()
    persist()


class TracerouteMeasure:
    """ This class helps to do a...
    """

    connection_builder = None

    def set_ConnectionBuilder(self, conBuilder):
        TracerouteMeasure.connection_builder = conBuilder

    def __init__(self, fromNode, toIP):
        """
            :param fromNode:    PlanetLab node IP address where traceroute will be executed
            :param toIP:        Target IP address for traceroute
        """
        self.fromIP     = fromNode
        self.toIP       = toIP
        self.toDNS      = None
        self.fromDNS    = None
        self.connection = None
        self.error      = None
        self.errorTrace = None
        self.rawResult  = None
        self.rawResults = []
        self.traceroute = None
        self.online     = None
        self.date       = getDate()
        self.timeStamp  = getTime()

    def connect(self):
        if self.error != None:
            return False
        self.timeStamp = getTime()
        self.online = ping(self.fromIP)
        if self.online:
            if not validIP(self.fromIP):
                self.fromDNS = self.fromIP
                self.fromIP = getIP_fromDNS(self.fromIP)
                if self.fromIP == None:
                    self.error = "not valid ip address or DNS name"
                    return False
            if not validIP(self.toIP):
                self.toDNS = self.toIP
                self.toIP = getIP_fromDNS(self.toIP)
                if self.fromIP == None:
                    self.error = "not valid ip address or DNS name"
                    return False
            try:
                self.connection = self.connection_builder.getConnection(self.fromIP)
                return True
            except paramiko.AuthenticationException:
                self.errorTrace = traceback.format_exc()
                self.error = "AuthenticationError"
                self.connection = None
                return False
            except paramiko.ssh_exception.BadHostKeyException:
                self.errorTrace = traceback.format_exc()
                self.error = "BadHostKeyException"
                self.connection = None
                return False
            except:
                self.errorTrace = traceback.format_exc()
                self.error = "ConnectionError"
                self.connection = None
                print "Error at connection:"
                print self.errorTrace
                return False

        self.errorTrace = "Offline"
        self.error = "Offline"
        return False

    def disconnect(self):
        if self.connection != None:
            self.connection.disconnect()

    def checkConnection(self):
        if self.error != None:
            return False
        if self.connection == None:
            self.errorTrace = "Not connected!"
            self.error = "ConnectionError"
            return False
        return True

    def runScript(self, name, skeleton, sudo=False):
        if self.error != None:
            return False
        try:
            command = skeleton%self.toIP
            if sudo:
                command = "sudo "+command

            self.timeStamp = getTime()
            outp, err = self.connection.runCommand(command)
        except IOError:
            self.errorTrace = traceback.format_exc()
            self.error = "IOError"
            return False
        except Exception:
            self.errorTrace = traceback.format_exc()
            self.error = "RemoteExecutionError"
            return False

        errLines = err.splitlines()
        if len(errLines) > 0:
            for line in errLines:
                if "bind" in line:
                    if sudo:
                        break
                    else:
                        return self.runScript(name, skeleton, sudo=True)
            self.errorTrace = err
            self.error = "RuntimeError"
            return False

        self.rawResults[name] = outp
        return True

    def runTraceroute(self, sudo=False):
        if self.error != None:
            return False
        #self.runScript("traceroute", traceroute_skeleton)

        try:
            command = traceroute_skeleton%self.toIP
            if sudo:
                command = "sudo "+command

            self.timeStamp = getTime()
            outp, err = self.connection.runCommand(command)
        except IOError:
            self.errorTrace = traceback.format_exc()
            self.error = "IOError"
            return False
        except Exception:
            self.errorTrace = traceback.format_exc()
            self.error = "RemoteExecutionError"
            return False

        errLines = err.splitlines()
        if len(errLines) > 0:
            for line in errLines:
                if "bind" in line:
                    if sudo:
                        break
                    else:
                        return self.runTraceroute(sudo=True)
            self.errorTrace = err
            self.error = "RuntimeError"
            return False

        self.rawResult = outp
        return True

    def connectAndMeasure(self):
        connected = self.connect()
        if connected:
            self.runMeasure()

    def runMeasure(self):
        if self.error != None:
            return False

        self.timeStamp_a = time()
        if not self.checkConnection():
            return False

        self.timeStamp_b = time()

        print "run traceroute"
        succesfulMeasure = self.runTraceroute()
        if not succesfulMeasure:
            return False

        self.timeStamp_c = time()

        try:
            print "parse traceroute"
            self.traceroute = trparse.loads(self.rawResult, self.fromIP)
        except:
            self.errorTrace = traceback.format_exc()
            self.error = "ParserError"
            return False

        self.timeStamp_d = time()
        return True

    def getData(self, sendError=True, sendErrorTrace=False):
        if not sendError and self.error != None:
            return None # we do not send errorous measurements

        res = { "date":   self.date,
                "time":   self.timeStamp,
                "online": self.online,
                "from":   self.fromIP,
                "to":     self.toIP}

        if sendError and self.error != None:
            res["error"] = self.error
            if sendErrorTrace:
                res["errorTrace"] = str(self.errorTrace)
        if self.error != None:
            return res#json.dumps(res)

        res["trace"] = self.rawResult

        return res#json.dumps(res)

    def getLinks(self):
        if self.error != None:
            return None
        prevIP = self.fromIP
        endIP  = self.toIP
        #parse.dest_name
        prevRTT    = 0
        index      = 0
        indexCheck = 0
        links      = []

        for hop in self.traceroute.hops:
            if hop.idx < indexCheck:
                raise Exception("Error in link sequence!")
            indexCheck = hop.idx
            avgRTT = 0
            probLen = 0
            mainProbe = None
            for probe in hop.probes:
                if probe == "*":
                    continue
                if mainProbe == None:
                    mainProbe = probe.ip
                if mainProbe == probe.ip and probe.rtt != None:
                    avgRTT += probe.rtt
                    probLen += 1
                #probe.ip
                #probe.name
                #probe.rtt
            if mainProbe == None:
                continue
            avgRTT /= probLen
            aktIP = mainProbe
            links.append([prevIP, aktIP, index, avgRTT, avgRTT-prevRTT])
            prevIP = aktIP
            index += 1
            prevRTT = avgRTT
        links.append([prevIP, endIP, index, 0, 0])
        return links

    def getIP_DNS_pairs(self):
        if self.error != None:
            return None
        pairs = []
        # prevIP = self.fromIP
        # pairs.append([self.fromIP, ])
        pairs.append([self.traceroute.dest_ip, self.traceroute.dest_name])

        for hop in self.traceroute.hops:
            for probe in hop.probes:
                if probe == "*":
                    continue
                pairs.append([probe.ip, probe.name])
        return pairs

def validIP(ip):
    numOfSegments = 0
    for segment in ip.split("."):
        numOfSegments += 1
        if not segment.isdigit() or int(segment) > 255:
            return False
    if numOfSegments != 4:
        return False
    return True

def getTime():
    now = datetime.now()
    return "{:0>2d}:{:0>2d}:{:0>2d}".format(now.hour, now.minute, now.second)

def getDate():
    today = date.today()
    return "{:d}.{:0>2d}.{:0>2d}".format(today.year, today.month, today.day)


connBuilder = ConnectionBuilder(slice_name, rsa_file, None)
TracerouteMeasure.connection_builder = connBuilder

if __name__ == "__main__":
    main()