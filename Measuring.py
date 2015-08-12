__author__ = 'Rudolf Horvath'
__date__ = "2015.06.15"

from RemoteScripting import *
from time import time
from datetime import date, datetime
import sys
import paramiko
import simplejson as json
import zlib
import base64
sys.path.append("utils")
import trparse


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
    # ip address - port - time - interval - bandwidth Mbitps
    start_client_skeleton = "iperf -c %s -p %d -u -t %d -i %d -b %dm -f m"

    def __init__(self, from_ip, to_ip, server_port=5200):
        Measure.__init__(self, from_ip, to_ip)
        self.iperf = None
        self.server_port = server_port
        self.fromIP     = from_ip
        self.toIP       = to_ip
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

    def _check_iperf_installation(self, con):
        cmd_test = "iperf -v"
        not_installed_test = "iperf: command not found"
        installed_test = "iperf version"
        if self.error != None:
            self.iperf_install = "Not checking install: Error at previous state"
            return False

        try:
            outp, err = con.runCommand(cmd_test)
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
        self.client = Connection(self.fromIP)
        self.client.connect()
        if self.client.error is not None:
            return False

        self._check_iperf_installation(self.client)

        if "installed" != self.iperf_install:
            return False

        cmd = self.start_client_skeleton %\
              (self.toIP, self.server_port)
        self.server.runCommand(cmd, timeout=duration+1)

    def _startServer(self):
        self.server = Connection(self.toIP)
        self.server.connect()
        if self.server.error is not None:
            return False

        self._check_iperf_installation(self.server)

        if "installed" != self.iperf_install:
            return False

        cmd = self.start_server_skeleton %\
              (self.toIP, self.server_port)
        self.server.startCommand(cmd)

    def _endServer(self):
        self.server.endCommand()

    def runIperf(self, duration, bandwidth=100, sudo=False):
        self.duration = duration
        self.bandwidth = bandwidth
        self._startServer()
        self._startClient(duration, bandwidth=bandwidth)
        self._endServer()
        return True

class ParalellMeasure:

    def addMeasure(self):
        pass

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
