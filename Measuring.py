__author__ = 'Rudolf Horvath'
__date__ = "2015.06.15"

from RemoteScripting import *
import time
from datetime import date, datetime
import sys
import paramiko
import simplejson as json
import zlib
import base64
sys.path.append("utils")
import trparse
import random
import logging


traceroute_skeleton = "traceroute -w 5.0 -q 3 %s"


#=================================================
# Classes


class Measure:
    """ This class helps to do a...
    """


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
        self.online     = None
        self.date       = getDate()
        self.timeStamp  = getTime()

    def connect(self):
        if self.error != None:
            return False
        self.timeStamp = time.getTime()
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
                self.connection = ConnectionBuilder.\
                    singleton.getConnection(self.fromIP)
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

            self.timeStamp = time.getTime()
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

        return res#json.dumps(res)


class IperfMeasure(Measure):

    # Interface, Port
    start_server_skeleton = 'iperf -s -B %s -u -p %d'
    # ip address - port - duration - interval - bandwidth Mbitps
    start_client_skeleton = "iperf -c %s -p %d -u -t %d -i %d -b %dm -f m"

    def __init__(self, from_ip, to_ip, server_username, server_port=5200, duration=None):
        Measure.__init__(self, from_ip, to_ip)
        self.iperf = None
        self.client = None
        self.server = None
        self.duration = duration
        self.server_port = server_port
        self.fromIP     = from_ip
        self.toIP       = to_ip
        self.toDNS      = None
        self.fromDNS    = None
        self.connection = None
        self.error      = None
        self.errorTrace = None
        self.rawResult  = None
        self.server_username = server_username
        self.rawResults = []
        self.online     = None
        self.date       = getDate()
        self.timeStamp  = getTime()
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id+".iperf")

    def _check_iperf_installation(self, con):
        cmd_test = "iperf -v"
        not_installed_test = "iperf: command not found"
        installed_test = "iperf version"
        if self.error != None:
            self.iperf_install = "Not checking install: Error at previous state"
            return False

        try:
            err, outp = con.runCommand(cmd_test)
        except Exception:
            self.iperf_install = "Error checking install: "+traceback.format_exc()
            return False

        errLines = err.splitlines()
        if len(errLines) > 0:
            self.iperf_install = "Error checking install: " + err
            return False

        if installed_test in outp:
            self.iperf_install = "installed"
            return True
        elif not_installed_test in outp:
            self.iperf_install = "not installed"
            return False
        else:
            self.iperf_install = "Error checking install: " + outp
            return False

    def _startClient(self, duration, interval=1, bandwidth=100):
        log = self.log.getChild("client")
        self.client = Connection(self.fromIP)
        log.info("Creating connection to remote target")
        self.client.connect()
        if self.client.error is not None:
            log.info("Abort because of a previous error: "+self.client.error+" ErrorTrace: "+self.client.errorTrace)
            return False

        self._check_iperf_installation(self.client)
        log.info("Iperf installation status: %s", self.iperf_install)

        if "installed" != self.iperf_install:
            log.info("Measurement aborted, iperf not installed")
            return False

        cmd = self.start_client_skeleton %\
              (self.toIP, self.server_port, duration, interval, bandwidth)
        log.info("Executing remote command: %s", cmd)
        self.client.startTime = time.time()
        self.client.stdout, self.client.stderr = self.server.runCommand(cmd, timeout=duration+5)
        log.info("Client ended")

        log.info("Output: %s", self.client.stdout)
        if len(self.client.stderr) > 0:
            log.info("Error at remote execution: %s", self.client.stderr)
            return False

        return True

    def _startServer(self):
        log = self.log.getChild("server")
        self.server = Connection(self.toIP, self.server_username)
        log.info("Creating connection to remote target")
        self.server.connect()
        if self.server.error is not None:
            log.info("Abort because of a previous error: "+self.server.error+" ErrorTrace: "+self.server.errorTrace)
            return False

        self._check_iperf_installation(self.server)
        log.info("Iperf installation status: %s", self.iperf_install)

        if "installed" != self.iperf_install:
            log.info("Measurement aborted, iperf not installed")
            return False

        cmd = self.start_server_skeleton %\
              (self.toIP, self.server_port)
        log.info("Executing remote command: %s", cmd)
        self.server.startCommand(cmd)
        log.info("Server started")
        return True

    def _endServer(self):
        self.log.info("Stopping server")
        self.server.endCommand()
        self.log.info("Server stopped")

    def runIperf(self, duration=None, bandwidth=100):
        if duration is None:
            duration = self.duration
        self.duration = duration
        self.bandwidth = bandwidth

        self.log.info("Starting server")
        successful = self._startServer()
        if not successful:
            self.log.info("Server starting failed, exiting measurement")
            self.error = "ClientError:"+self.server.error
            self.errorTrace = self.server.errorTrace
            return

        self.log.info("Starting client")
        successful = self._startClient(duration, bandwidth=bandwidth)
        if not successful:
            self.log.info("Client starting failed, exiting measurement")
            self.error = "ClientError:"+self.client.error
            self.errorTrace = self.client.errorTrace
            return

        self._endServer()
        self.log.info("Measure ended")

    def run(self):
        self.runIperf()

    def getData(self, sendError=True, sendErrorTrace=False):
        res = Measure.getData(self, sendError, sendErrorTrace)
        if self.client is None or self.server is None:
            return {"error": "MeasureNotStarted"}

        res["iperf"] = self.client.stdout
        res["online"] = self.server.online and self.client.online
        if self.error is None:
            res["serverStart"] = self.server.startTime
            res["serverEnd"] = self.server.endTime
            res["clientStart"] = self.client.startTime
        return res


class ParalellMeasure:

    def __init__(self):
        self.measures = []

    def addMeasure(self, measure, startTime):
        self.measures.append({"measure": measure, "startTime": startTime})

    def startMeasure(self):
        self.measures = sorted(self.measures, key=lambda k: k['startTime'])

        def run(measure):
            measure.run()

        start = time.time()
        for item in self.measures:
            dist = start-time.time()+item["startTime"]
            print "dist: ", dist
            if dist > 0:
                time.sleep(dist)
            thread = Thread(target=run, args=(item["measure"], ))
            thread.start()
            item["thread"] = thread

        print self.measures

    def join(self):
        for item in self.measures:
            item["thread"].join()

    def getData(self):
        res = []

        for item in self.measures:
            res.append(item["measure"].getData())

        return res


class TracerouteMeasure(Measure):

    def __init__(self, from_ip, to_ip):
        Measure.__init__(self, from_ip, to_ip)
        self.traceroute = None


    def getData(self, sendError=True, sendErrorTrace=False):
        res = Measure.getData(self, sendError, sendErrorTrace)
        if self.error is None:
            res["trace"] = self.rawResult
        return res

    def runTraceroute(self, sudo=False):
        if self.error != None:
            return False
        #self.runScript("traceroute", traceroute_skeleton)

        try:
            command = traceroute_skeleton%self.toIP
            if sudo:
                command = "sudo "+command

            self.timeStamp = time.getTime()
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

    def run(self):
        self.runTraceroute()

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


#=================================================
# Functions


def getTime():
    now = datetime.now()
    return "{:0>2d}:{:0>2d}:{:0>2d}".format(now.hour, now.minute, now.second)


def getDate():
    today = date.today()
    return "{:d}.{:0>2d}.{:0>2d}".format(today.year, today.month, today.day)
