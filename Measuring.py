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

class Measure:
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
        """
        try:
            print "parse traceroute"
            self.traceroute = trparse.loads(self.rawResult, self.fromIP)
        except:
            self.errorTrace = traceback.format_exc()
            self.error = "ParserError"
            return False
        self.timeStamp_d = time()
        """
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
    """
    http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-14&arch=i386
    """

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
