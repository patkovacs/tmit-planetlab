__author__ = 'Rudolf Horvath'
__date__ = "2015.06.15"

import sys
sys.path.append("utils")
from RemoteScripting import *
import time
from datetime import date, datetime
import paramiko
import simplejson as json
import zlib
import base64
import trparse
import random
import logging
from ASN_Lookup import get_asn
from Geoloc_Lookup import get_geoloc
import threading


traceroute_skeleton = "traceroute -w 5.0 -q 3 %s"


#=================================================
# Classes


class Measure:
    """ This class helps to do a...
    """


    def __init__(self, fromIP, toIP, login_username=None):
        """
            :param fromIP:    PlanetLab node IP address where traceroute will be executed
            :param toIP:        Target IP address for traceroute
        """
        self.fromIP     = fromIP
        self.toIP       = toIP
        self.login_username = login_username
        self.toDNS      = None
        self.fromDNS    = None
        self.connection = None
        self.error      = None
        self.errorTrace = None
        self.rawResult  = None
        self.rawResults = {}
        self.online     = None
        self.timeout    = 10
        self.date       = getDate()
        self.timeStamp  = getTime()
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id+".measure")

    def setScript(self, name, script, timeout = 10):
        self.script = script
        self.name = name
        self.timeout = timeout
        self.log = logging.getLogger().getChild(self.id+"."+name)
        self.log.info('Set script with name "%s": %s' % (name, script))

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

    def run(self):
        self.runScript(self.name, self.script)

    def end(self):
        self.log.info("Ending script running")
        self.disconnect()
        self.log.info("Ended script running")
        #self.thread.end()

    def start(self):
        return self.startScript(self.name, self.script, self.timeout)

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

    def runScript(self, name, skeleton, sudo=False, timeout=10):
        log = self.log.info
        log("Running script '%s': %s" % (name, skeleton))
        if self.error != None:
            log("Script running aborted because of a previous error:"+self.error)
            log("Errortrace of previous error:"+self.errorTrace)
            return False

        self.connection = Connection(self.fromIP, self.login_username)
        log("Creating connection to remote target")
        self.connection.connect()
        self.online = self.connection.online
        self.error = self.connection.error
        self.errorTrace = self.connection.errorTrace

        if self.connection.error is not None:
            log("Abort because of a previous error: "+self.connection.error+\
                " ErrorTrace: "+self.connection.errorTrace)
            return False

        try:
            try:
                command = skeleton%self.toIP
            except:
                command = skeleton

            if sudo:
                command = "sudo "+command

            self.timeStamp = time.time()
            log("Executing script: "+command)
            outp, err = self.connection.runCommand(command, timeout = timeout)
        except IOError:
            self.errorTrace = traceback.format_exc()
            self.error = "IOError"
            log("Error at execution: IOError:\n"+self.errorTrace)
            return False
        except Exception:
            self.errorTrace = traceback.format_exc()
            self.error = "RemoteExecutionError"
            log("Error at execution: "+self.errorTrace)
            return False

        errLines = err.splitlines()
        if len(errLines) > 0:
            for line in errLines:
                if "bind" in line:
                    if sudo:
                        break
                    else:
                        log.info("Failed executing remote script, retrying with sudo. ErrorTrace: "+err)
                        return self.runScript(name, skeleton, sudo=True)
            self.errorTrace = err
            self.error = "RuntimeError"
            log("Error at execution (runtime): "+self.errorTrace)
            return False

        self.rawResults[name] = outp
        log("Script excecution suceed: "+outp)
        return True

    def startScript(self, name, skeleton, timeout = 10):
        self.log.info("Starting remote execution on new thread "\
                      "(name: '%s', command: %s)" % (name, skeleton))
        thread = Thread(target=self.runScript,
                        args=(name, skeleton), kwargs={"timeout": timeout})
        thread.start()
        self.thread = thread
        return thread

    def getData(self, sendError=True, sendErrorTrace=False):
        if not sendError and self.error != None:
            return None # we do not send errorous measurements

        res = { "date":   self.date,
                "time":   self.timeStamp,
                "online": self.online,
                "from":   self.fromIP,
                "to":     self.toIP}

        if len(self.rawResults) > 0:
            res["name"] = self.name
            res["result"] = self.rawResults[self.name]

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
    start_client_skeleton = "iperf -c %s -p %d -u -t %d -i %d -b %dm -f m -i 1"

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
            self.client.error = "IperfNotInstalled"
            self.client.errorTrace = self.client.error
            return False

        cmd = self.start_client_skeleton %\
              (self.toIP, self.server_port, duration, interval, bandwidth)
        log.info("Executing remote command: %s", cmd)
        self.client.startTime = time.time()
        self.client.stdout, self.client.stderr = self.server.runCommand(cmd, timeout=duration+5)
        log.info("Client ended")

        log.info("Output: %s", self.client.stdout)
        if len(self.client.stderr) > 0 and "WARNING:" not in self.client.stderr:
            log.info("Error at remote execution: %s", self.client.stderr)
            self.client.error = "RemoteRuntimeError"
            self.client.errorTrace = self.client.stderr
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
        self.log.info("Server output: "+self.server.stdout)
        self.log.info("Server error: "+self.server.stderr)

    def runIperf(self, duration=None, bandwidth=20):
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

        time.sleep(2)
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

    def addMeasure(self, measure, startTime, onThread=False, duration=None):
        self.measures.append({
            "measure": measure,
            "startTime": startTime,
            "onThread": onThread,
            "duration": duration
        })

    def startMeasure(self):
        self.measures = sorted(self.measures, key=lambda k: k['startTime'])

        def run(measure):
            measure.run()

        start = time.time()
        for item in self.measures:
            dist = start-time.time()+item["startTime"]
            if dist > 0:
                time.sleep(dist)
            if item["onThread"]:
                thread = item["measure"].start()
                item["thread"] = thread
                item["shutdown"] = threading.Timer(item["duration"],
                                           item["measure"].end)
                item["shutdown"].start()

            else:
                thread = Thread(target=run, args=(item["measure"], ))
                thread.start()
                item["thread"] = thread

        print self.measures

    def join(self):
        for item in self.measures:
            item["thread"].join()
            if item.has_key("shutdown"):
                item["shutdown"].cancel()
                item["shutdown"].join()

    def getData(self, sendError=True, sendErrorTrace=False):
        res = []

        for item in self.measures:
            res.append(item["measure"].getData(sendError, sendErrorTrace))

        return res


class TracerouteMeasure(Measure):

    def __init__(self, from_ip, to_ip):
        Measure.__init__(self, from_ip, to_ip)
        self.traceroute = None
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id+".traceroute")


    def getData(self, sendError=True, sendErrorTrace=False):
        res = Measure.getData(self, sendError, sendErrorTrace)
        if self.error is None:
            res["trace"] = self.rawResult

        if len(self.ip_data) > 0:
            res["ip_data"] = self.ip_data

        return res

    def runTraceroute(self, sudo=False):
        log = self.log

        self.connection = Connection(self.fromIP)
        log.info("Creating connection to remote target")
        self.connection.connect()
        self.online = self.connection.online
        self.error = self.connection.error
        self.errorTrace = self.connection.errorTrace
        if self.connection.error is not None:
            log.info("Abort because of connection error: "+self.connection.error+" ErrorTrace: "+self.connection.errorTrace)
            return False


        if self.error != None:
            log.info("measurement aborted because of a previous error: "+self.error)
            return False
        #self.runScript("traceroute", traceroute_skeleton)

        try:
            command = traceroute_skeleton%self.toIP
            if sudo:
                command = "sudo "+command

            self.timeStamp = time.time()
            outp, err = self.connection.runCommand(command)
        except IOError:
            self.errorTrace = traceback.format_exc()
            self.error = "IOError"
            log.info("IOError!")
            return False
        except Exception:
            self.errorTrace = traceback.format_exc()
            self.error = "Error executing remote command"
            log.info("Error at remote execution: "+self.errorTrace)
            return False

        errLines = err.splitlines()
        if len(errLines) > 0:
            for line in errLines:
                if "bind" in line:
                    log.info("retrying with sudo")
                    if sudo:
                        break
                    else:
                        return self.runTraceroute(sudo=True)
            self.errorTrace = err
            self.error = "RuntimeError"
            log.info("Runtime error: "+err)
            return False

        self.rawResult = outp
        return True

    def run(self):
        self.runTraceroute()
        self.traceroute = trparse.loads(self.rawResult, self.fromIP)
        self.links = self.getLinks()
        if self.links is None:
            return
        self.ip_list = []
        for link in self.links:
            if link[0] not in self.ip_list:
                self.ip_list.append(link[0])
            if link[1] not in self.ip_list:
                self.ip_list.append(link[1])

        self.ip_data = []
        for ip in self.ip_list:
            print "ip: ", ip
            akt = get_geoloc(ip)
            #if akt["asn"] == "":
            #    akt["asn"] = get_asn(ip)
            print "data: ", akt
            self.ip_data.append(get_geoloc(ip))

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
