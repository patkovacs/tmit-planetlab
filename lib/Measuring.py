import sys
import time
from datetime import date, datetime
import threading
from threading import Thread
import traceback
import logging
import simplejson as json
import re

sys.path.append("utils")
import utils
import lib

# =================================================
# Classes


class Measure:
    """ This class helps to do a...
    """

    def __init__(self, fromIP, toIP, login_username=None):
        """
            :param fromIP:    PlanetLab node IP address where traceroute will be executed
            :param toIP:        Target IP address for traceroute
        """
        self.fromIP = fromIP
        self.toIP = toIP
        self.login_username = login_username
        self.toDNS = None
        self.fromDNS = None
        self.connection = None
        self.error = None
        self.errorTrace = None
        self.rawResult = None
        self.rawResults = {}
        self.online = None
        self.timeout = 10
        self.date = get_date()
        self.timeStamp = get_time()
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id + ".measure")

    def setScript(self, name, script, timeout=10):
        self.script = script
        self.name = name
        self.timeout = timeout
        self.log = logging.getLogger().getChild(self.id + "." + name)
        self.log.info('Set script with name "%s": %s' % (name, script))

    def connect(self):
        log = self.log

        self.connection = lib.Connection(self.fromIP)
        log.info("Creating connection to remote target")
        self.connection.connect()
        self.online = self.connection.online
        self.error = self.connection.error
        self.errorTrace = self.connection.errorTrace
        if self.connection.error is not None:
            log.info(
                "Abort because of connection error: " + self.connection.error + " ErrorTrace: " + self.connection.errorTrace)
            return False
        return True

    def run(self):
        self.runScript(self.name, self.script)

    def end(self):
        self.log.info("Ending script running")
        self.disconnect()
        self.log.info("Ended script running")
        # self.thread.end()

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
            log("Script running aborted because of a previous error:" + self.error)
            log("Errortrace of previous error:" + self.errorTrace)
            return False

        self.connection = lib.Connection(self.fromIP, self.login_username)
        log("Creating connection to remote target")
        self.connection.connect()
        self.online = self.connection.online
        self.error = self.connection.error
        self.errorTrace = self.connection.errorTrace

        if self.connection.error is not None:
            log("Abort because of a previous error: " + self.connection.error + \
                " ErrorTrace: " + self.connection.errorTrace)
            return False

        try:
            try:
                command = skeleton % self.toIP
            except:
                command = skeleton

            if sudo:
                command = "sudo " + command

            self.timeStamp = time.time()
            log("Executing script: " + command)
            outp, err = self.connection.runCommand(command, timeout=timeout)
        except IOError:
            self.errorTrace = traceback.format_exc()
            self.error = "IOError"
            log("Error at execution: IOError:\n" + self.errorTrace)
            return False
        except Exception:
            self.errorTrace = traceback.format_exc()
            self.error = "RemoteExecutionError"
            log("Error at execution: " + self.errorTrace)
            return False

        errLines = err.splitlines()
        if len(errLines) > 0:
            for line in errLines:
                if "bind" in line:
                    if sudo:
                        break
                    else:
                        log.info("Failed executing remote script, retrying with sudo. ErrorTrace: " + err)
                        return self.runScript(name, skeleton, sudo=True)
            self.errorTrace = err
            self.error = "RuntimeError"
            log("Error at execution (runtime): " + self.errorTrace)
            return False

        self.rawResults[name] = outp
        log("Script excecution suceed: " + outp)
        return True

    def startScript(self, name, skeleton, timeout=10):
        self.log.info("Starting remote execution on new thread " \
                      "(name: '%s', command: %s)" % (name, skeleton))
        thread = Thread(target=self.runScript,
                        args=(name, skeleton), kwargs={"timeout": timeout})
        thread.start()
        self.thread = thread
        return thread

    def getData(self, sendError=True, sendErrorTrace=False):
        if not sendError and self.error != None:
            return None  # we do not send errorous measurements

        res = {"date": self.date,
               "time": self.timeStamp,
               "online": self.online,
               "from": self.fromIP,
               "to": self.toIP}

        if len(self.rawResults) > 0:
            res["name"] = self.name
            res["result"] = self.rawResults[self.name]

        if sendError and self.error != None:
            res["error"] = self.error
            if sendErrorTrace:
                res["errorTrace"] = str(self.errorTrace)
        if self.error != None:
            return res  # json.dumps(res)

        return res  # json.dumps(res)


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
        self.fromIP = from_ip
        self.toIP = to_ip
        self.toDNS = None
        self.fromDNS = None
        self.connection = None
        self.error = None
        self.errorTrace = None
        self.rawResult = None
        self.server_username = server_username
        self.rawResults = []
        self.online = None
        self.date = get_date()
        self.timeStamp = get_time()
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id + ".iperf")

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
            self.iperf_install = "Error checking install: " + traceback.format_exc()
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
        self.client = lib.Connection(self.fromIP)
        log.info("Creating connection to remote target")
        self.client.connect()
        if self.client.error is not None:
            log.info(
                "Abort because of a previous error: " + self.client.error + " ErrorTrace: " + self.client.errorTrace)
            return False

        self._check_iperf_installation(self.client)
        log.info("Iperf installation status: %s", self.iperf_install)

        if "installed" != self.iperf_install:
            log.info("Measurement aborted, iperf not installed")
            self.client.error = "IperfNotInstalled"
            self.client.errorTrace = self.client.error
            return False

        cmd = self.start_client_skeleton % \
              (self.toIP, self.server_port, duration, interval, bandwidth)
        log.info("Executing remote command: %s", cmd)
        self.client.startTime = time.time()
        self.client.stdout, self.client.stderr = self.server.runCommand(cmd, timeout=duration + 5)
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
        self.server = lib.Connection(self.toIP, self.server_username)
        log.info("Creating connection to remote target")
        self.server.connect()
        if self.server.error is not None:
            log.info(
                "Abort because of a previous error: " + self.server.error + " ErrorTrace: " + self.server.errorTrace)
            return False

        self._check_iperf_installation(self.server)
        log.info("Iperf installation status: %s", self.iperf_install)

        if "installed" != self.iperf_install:
            log.info("Measurement aborted, iperf not installed")
            return False

        cmd = self.start_server_skeleton % \
              (self.toIP, self.server_port)
        log.info("Executing remote command: %s", cmd)
        self.server.startCommand(cmd)
        log.info("Server started")
        return True

    def _endServer(self):
        self.log.info("Stopping server")
        self.server.endCommand()
        self.log.info("Server stopped")
        self.log.info("Server output: " + self.server.stdout)
        self.log.info("Server error: " + self.server.stderr)

    def runIperf(self, duration=None, bandwidth=20):
        if duration is None:
            duration = self.duration
        self.duration = duration
        self.bandwidth = bandwidth

        self.log.info("Starting server")
        successful = self._startServer()
        if not successful:
            self.log.info("Server starting failed, exiting measurement")
            self.error = "ClientError:" + self.server.error
            self.errorTrace = self.server.errorTrace
            return

        time.sleep(2)
        self.log.info("Starting client")
        successful = self._startClient(duration, bandwidth=bandwidth)
        if not successful:
            self.log.info("Client starting failed, exiting measurement")
            self.error = "ClientError:" + self.client.error
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

class ITGMeasure(Measure):
    """Measuring with D-ITG"""
    #ITGRecv
    start_server_skeleton = 'ITGRecv'
    #ITGSend -a <destination address> -T <protocol[UDP(default),TCP,ICMP,SCTP,DCCP] -c <pkt_size> -C <rate> -t <duration> -x <receiver-logfile name>
    start_client_skeleton = "ITGSend -a %s -T %s -c %i -C %i -t %i -x %s"

    #to_ip = mptcp from_ip=planetlabos client server_username=mptcp
    def __init__(self, from_ip, to_ip, server_username, server_port=8999, duration=None):
        Measure.__init__(self, from_ip, to_ip)
        self.itg_installed = None
        self.client = None
        self.server = None
        self.duration = duration
        self.server_port = server_port
        self.fromIP = from_ip
        self.toIP = to_ip
        self.toDNS = None
        self.fromDNS = None
        self.connection = None
        self.error = None
        self.errorTrace = None
        self.rawResult = None
        self.server_username = server_username
        self.rawResults = []
        self.online = None
        self.date = get_date()
        self.timeStamp = get_time()
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id + ".itg")

    def _check_DITG_installation(self, con):
        cmd_test = "ITGSend -v"
        not_installed_test = "ITGSend: command not found"
        installed_test = "ITGSend version"
        if self.error != None:
            self.itg_install = "Not checking install: Error at previous state"
            return False

        try:
            err, outp = con.runCommand(cmd_test)
        except Exception:
            print traceback.format_exc()
            return False

        if installed_test in outp or installed_test in err:
            self.itg_installed = "installed"
            return True
        elif not_installed_test in outp:
            self.itg_installed = "not installed"
            self.itg_not_installed()
            return False
        return False

    def itg_not_installed(self):
        with open("not_installed","a") as file:
            file.write(self.fromIP+'\n')

    def _startClient(self,protocol="UDP", pkt_size=512,rate=1000,duration=10000,receive_logfile_name="receive_log_file_"):
        log = self.log.getChild("client")
        receive_logfile_name = receive_logfile_name + self.toIP
        self.client = lib.Connection(self.fromIP)
        log.info("Creating connection to remote target")
        self.client.connect()
        if self.client.error is not None:
            log.info(
                "Abort because of a previous error: " + self.client.error + " ErrorTrace: " + self.client.errorTrace)
            return False

        self._check_DITG_installation(self.client)

        if "installed" != self.itg_installed:
            log.info("Measurement aborted, D-ITG not installed")
            self.client.error = "D-ITGNotInstalled"
            self.client.errorTrace = self.client.error
            return False

        #ITGSend -a <destination address> -T <protocol[UDP(default),TCP,ICMP,SCTP,DCCP] -c <pkt_size> -C <rate> -t <duration> -x <receiver-logfile name>
        cmd = self.start_client_skeleton % \
              (self.toIP, protocol, pkt_size, rate, duration, receive_logfile_name)
        log.info("Executing remote command: %s", cmd)
        self.client.startTime = time.time()
        self.client.stdout, self.client.stderr = self.client.runCommand(cmd, timeout=duration + 5)
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
        self.server = lib.Connection(self.toIP, self.server_username)
        log.info("Creating connection to remote target")
        self.server.connect()
        if self.server.error is not None:
            log.info(
                "Abort because of a previous error: " + self.server.error + " ErrorTrace: " + self.server.errorTrace)
            return False

        self._check_DITG_installation(self.server)

        if "installed" != self.itg_installed:
            log.info("Measurement aborted, D-ITG not installed")
            self.server.error="ITG not installed"
            return False
         #ITGRecv
        cmd = self.start_server_skeleton
        log.info("Executing remote command: %s", cmd)
        output = self.server.startCommand(cmd)
        print output
        log.info("Server started")
        return True

    def _endServer(self):
        self.log.info("Stopping server")
        self.server.endCommand()
        self.log.info("Server stopped")
        self.log.info("Server output: " + self.server.stdout)
        self.log.info("Server error: " + self.server.stderr)

    def runITG(self,receive_log_file=None,send_log_file=None,duration=None,pkt_size=None,rate=None):
        if duration is None:
            duration = self.duration
        else:
            self.duration = duration
        self.log.info("Starting server")
        successful = self._startServer()
        if not successful:
            self.log.info("Server starting failed, exiting measurement")
            self.error = "ClientError:" + self.server.error
            self.errorTrace = self.server.errorTrace
            return

        time.sleep(2)
        self.log.info("Starting client")
        successful = self._startClient()
        if not successful:
            self.log.info("Client starting failed, exiting measurement")
            self.error = "ClientError:" + self.client.error
            self.errorTrace = self.client.errorTrace
            return

        self._endServer()
        self.log.info("Measure ended")
        res = self.getData()
        print res.keys()
        print res["date"]

    def run(self):
        self.runITG()

    def start(self, timeout=10):
        #self.log.info("Starting remote execution on new thread " \
        #             "(name: '%s', command: %s)" % (name, skeleton))
        thread = Thread(target=self.run)
        thread.start()
        self.thread = thread
        return thread

    def end(self):
        print "END Called"

    def getData(self, sendError=True, sendErrorTrace=False):
        res = Measure.getData(self, sendError, sendErrorTrace)
        if self.client is None or self.server is None:
            return {"error": "MeasureNotStarted"}

        res["itg"] = self.client.stdout
        res["online"] = self.server.online and self.client.online
        if self.error is None:
            res["serverStart"] = self.server.startTime
            res["serverEnd"] = self.server.endTime
            res["clientStart"] = self.client.startTime
        self.create_json(res)
        return res

    def create_json(self,res,receive_logfile_name="receive_log_file_"):
        log = self.log.getChild("log")
        receive_logfile_name = receive_logfile_name + self.toIP
        self.server = lib.Connection(self.toIP, self.server_username)
        log.info("Creating connection to remote target")
        self.server.connect()
        if self.server.error is not None:
            log.info(
                "Abort because of a previous error: " + self.server.error + " ErrorTrace: " + self.server.errorTrace)
            return False

        self._check_DITG_installation(self.server)

        if "installed" != self.itg_installed:
            log.info("Measurement aborted, D-ITG not installed")
            self.server.error="ITG not installed"
            return False
         #ITGDec
        cmd = "ITGDec "+receive_logfile_name
        log.info("Executing remote command: %s", cmd)
        stdout,stderr = self.server.runCommand(cmd)
        res["itg"]=stdout
        print res["itg"]

        result_json = {}
        result_json["from"]=res["from"]
        result_json["to"]=res["to"]
        result_json["time"]=res["time"]
        result_json["date"]=res["date"]

        lists = res["itg"].split("\n")
        splitted = []
        for l in lists:
            if "=" in l:
                splitted.append(l.replace(" ",""))
        dictin=[]
        for s in splitted[0:11]:
            result_json[s.split("=")[0]]=float(re.findall(r'\d+[\.]?\d*',s.split("=")[1])[0])
        with open(result_json["date"]+".json","a") as file:
            json.dump(result_json,file)
            file.write("\n")
        self.delete_log_file(receive_logfile_name)

    def delete_log_file(self,receive_logfile_name):
        cmd = "rm "+receive_logfile_name
        self.server.runCommand(cmd)


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
            dist = start - time.time() + item["startTime"]
            if dist > 0:
                time.sleep(dist)
            if item["onThread"]:
                thread = item["measure"].start()
                item["thread"] = thread
                item["shutdown"] = threading.Timer(item["duration"],
                                                   item["measure"].end)
                item["shutdown"].start()

            else:
                thread = Thread(target=run, args=(item["measure"],))
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
        # print "paralell measures: ", self.measures
        timestamp = None
        for item in self.measures:
            # print "Item: ", item
            # print "Error: ", item["measure"].error
            data = item["measure"].getData(sendError, sendErrorTrace)
            #if timestamp is None:
            #    timestamp = data["time"]
            res.append(data)

        return {"result": res, "name": "ParalellIperf", "time": timestamp}


class TracerouteMeasure(Measure):
    traceroute_skeleton = "traceroute -w 5.0 -q 20 %s"

    def __init__(self, from_ip, to_ip):
        Measure.__init__(self, from_ip, to_ip)
        self.traceroute = None
        self.id = str(self.fromIP).replace(".", "_")
        self.log = logging.getLogger().getChild(self.id + ".traceroute")

    def getData(self, sendError=True, sendErrorTrace=False):
        res = Measure.getData(self, sendError, sendErrorTrace)
        if self.error is None:
            res["trace"] = self.rawResult

        if len(self.ip_data) > 0:
            res["ip_data"] = self.ip_data

        return res

    def runTraceroute(self, sudo=False):
        log = self.log

        self.connection = lib.Connection(self.fromIP)
        log.info("Creating connection to remote target")
        self.connection.connect()
        self.online = self.connection.online
        self.error = self.connection.error
        self.errorTrace = self.connection.errorTrace
        if self.connection.error is not None:
            log.info(
                "Abort because of connection error: " + self.connection.error + " ErrorTrace: " + self.connection.errorTrace)
            return False

        if self.error is not None:
            log.info("measurement aborted because of a previous error: " + self.error)
            return False
        # self.runScript("traceroute", traceroute_skeleton)

        try:
            command = self.traceroute_skeleton % self.toIP
            if sudo:
                command = "sudo " + command

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
            log.info("Error at remote execution: " + self.errorTrace)
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
            log.info("Runtime error: " + err)
            return False

        self.rawResult = outp
        return True

    def run(self):
        self.runTraceroute()
        self.traceroute = utils.trparse.loads(self.rawResult, self.fromIP)
        self.links = self.get_links()
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
            akt = utils.get_geoloc(ip)
            # if akt["asn"] == "":
            #    akt["asn"] = get_asn(ip)
            print "data: ", akt
            self.ip_data.append(utils.get_geoloc(ip))

    def get_links(self):
        if self.error != None:
            return None
        prevIP = self.fromIP
        endIP = self.toIP
        # parse.dest_name
        prevRTT = 0
        index = 0
        indexCheck = 0
        links = []

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
                    # probe.ip
                    # probe.name
                    # probe.rtt
            if mainProbe == None:
                continue
            avgRTT /= probLen
            aktIP = mainProbe
            links.append([prevIP, aktIP, index, avgRTT, avgRTT - prevRTT])
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


# =================================================
# Functions


def get_time():
    now = datetime.now()
    return "{:0>2d}:{:0>2d}:{:0>2d}".format(now.hour, now.minute, now.second)


def get_date():
    today = date.today()
    return "{:d}.{:0>2d}.{:0>2d}".format(today.year, today.month, today.day)
