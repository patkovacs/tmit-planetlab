import os
import sys
import subprocess
import traceback
import socket
from threading import Thread
import time
import logging
import platform
import simplejson as json
import paramiko
import xmlrpclib
from collections import Counter

sys.path.append("utils")
import lib
import utils


# Constants
API_URL = 'https://www.planet-lab.eu:443/PLCAPI/'
PLC_CREDENTIALS = 'ssh_needs/credentials.private'
slice_name = 'budapestple_cloud'


#=================================================
# Classes


class Connection:
    """ This class represents an SSH connection to a remote server.
        It can be used to run c
    """
    connection_builder = None


    def __init__(self, ip, username=None, conBuilder=None):
        if conBuilder is None:
            self.conBuilder = Connection.connection_builder
        else:
            self.conBuilder = conBuilder
        self.ip = ip
        self.username= username
        self.ssh = None
        self.online = None
        self.error = None
        self.errorTrace = None
        id = str(ip).replace(".", "_")
        self.log = logging.getLogger(id+".connection")

    def connect(self, timeout=5):
        info, self.ssh = self.conBuilder.\
            getConnectionSafe(self.ip, self.username)

        self.online = info["online"]
        self.error = info["error"]
        self.errorTrace = info["errorTrace"]
        self.ip = info["ip"]
        self.dns = info["dns"]
        self.stderr = None
        self.stdout = None
        self.log.info("connection result: "+json.dumps(info))

        return self.online and self.error is None

    def testOS(self):
        # TODO: Test it!
        cmd = "cat /etc/issue"
        os_names = ["Linux", "Ubuntu", "Debian", "Fedora", "Red Hat", "CentOS"]
        result = {}

        try:
            outp, err = self.runCommand(cmd)
        except Exception:
            error_lines = traceback.format_exc().splitlines()
            result["error"] = error_lines[-1]
            return result

        if len(err) > 0:
            result["error"] = err
            return result

        result["outp"] = outp

        # Check for official distribution name in output
        if any([os_name.lower() in result["os"].lower()
                for os_name in os_names]):
            result["os"] = outp.split("\n")[0]

        return result

    def endCommand(self):

        self.disconnect()

        if self.stderr is not None and len(self.stderr) > 0:
            self.error = "RuntimeError"
            self.errorTrace = self.stderr

    def startCommand(self, script):
        if self.ssh == None:
            raise RuntimeWarning("Connection not alive!")

        def run(self):
            self.running = True
            self.ended = False
            self.startTime = time.time()
            try:
                self.stdout, self.stderr = \
                    self.runCommand(script, timeout=None)
            except Exception:
                self.errorTrace = traceback.format_exc()
                self.error = "ErrorExecutingRemoteCommand:"+\
                    self.errorTrace.splitlines()[-1]
            else:
                self.endTime = time.time()
                if "timeout: timed out" in self.stderr:
                    self.error = "SSH connection timeout. duration: %d" % (self.endTime - self.startTime)
            self.endTime = time.time()
            self.running = False
            self.ended = True

        self.thread = Thread(target=run, args=(self, ))

        self.thread.start()

    def runCommand(self, command, timeout=5):
        if self.ssh is None:
            raise RuntimeWarning("Connection not alive!")

        stdin, stdout, stderr = self.ssh.exec_command(command,
                                                      timeout=timeout,
                                                      get_pty=True)

        output = stdout.read()
        errors = stderr.read()
        return output, errors

    def disconnect(self):
        if self.ssh is not None:
            self.ssh.close()
        self.ssh = None


class ConnectionBuilder:
    """ This class helps to build up an SSH connection to a remote server.
    """

    def __init__(self, slice_name, private_key, knownHosts=None):
        """ :param slice_name: Username used to login
            :param private_key: RSA private key filename
            :param knownHosts: if not given, autoAddPolicy is set,
                                which is not recommended
        """
        self.slice_name = slice_name
        self.private_key = private_key
        self.knownHosts = knownHosts

    def getConnection(self, target, username=None, timeout=5):
        ssh = paramiko.SSHClient()
        #paramiko.util.log_to_file("paramiko.log")

        if self.knownHosts != None:
            ssh.load_host_keys(self.knownHosts)
            ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        else:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if username is None:
            username = self.slice_name

        ssh.connect(target, username=username, key_filename=self.private_key, timeout=timeout)
        return ssh

    def getConnectionSafe(self, target, username=None, timeout=5):
        info = {}
        info["ip"] = target
        info["dns"] = target
        info["error"] = None
        info["errorTrace"] = None

        if not is_valid_ip(target):
            info["ip"] = getIP_fromDNS(target)
            if info["ip"] == None:
                info["online"] = False
                info["error"] = "AddressError"
                info["errorTrace"] = "not valid ip address or DNS name"
                return info, None

        info["online"] = ping(info["ip"])
        if info["online"]:
            try:
                con = self.getConnection(info["ip"], username, timeout)
                return info, con
            except paramiko.AuthenticationException:
                info["errorTrace"] = traceback.format_exc()
                info["error"] = "AuthenticationError"
                return info, None
            except paramiko.BadHostKeyException:
                info["errorTrace"] = traceback.format_exc()
                info["error"] = "BadHostKeyError"
                return info, None
            except:
                info["errorTrace"] = traceback.format_exc()
                info["error"] = "ConnectionError"
                return info, None

        info["errorTrace"] = "Offline"
        info["error"] = "Offline"
        return info, None


#=================================================
# Functions to help contacting the PlanetLab nodes

def set_ssh_data(username, rsa_key, known_hosts):
    Connection.connection_builder = \
        ConnectionBuilder(slice_name, rsa_key, known_hosts)


def getBestNodes():
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


def check_itg(node):
    log_id = str(node).replace(".", "_") + ".checkIperf"
    log = logging.getLogger().getChild(log_id).info

    cmd_test = "ITGSend -v"
    not_installed_test = "ITGSend: command not found"
    installed_test = "ITGSend version"
    try:
        con = Connection(node)
        con.connect()
        if con.errorTrace is not None:
            log("Error at connection: " + con.errorTrace)
    except Exception:
        #log("Error at connection: " + traceback.format_exc())
        return False

    try:
        err, outp = con.runCommand(cmd_test)
    except Exception:
        print traceback.format_exc()
        return False

    if installed_test in outp or installed_test in err:
        itg_installed = "installed"
        return True
    elif not_installed_test in outp:
        itg_installed = "not installed"
        return False
    return False


def getPlanetLabNodes(slice_name):
    global PLC_CREDENTIALS, API_URL

    plc_api = xmlrpclib.ServerProxy(API_URL, allow_none=True)
    cred    = open(PLC_CREDENTIALS,'r')

    auth = { 'AuthMethod' : 'password',
             'Username' : cred.readline().split('\n')[0],
             'AuthString' : cred.readline().split('\n')[0],
    }

    # the slice's node ids
    try:
        node_ids = plc_api.GetSlices(auth, slice_name, ['node_ids'])[0]['node_ids']
        node_hostnames = plc_api.GetNodes(auth,node_ids,['hostname'])
        return [item["hostname"] for item in node_hostnames]
    except:
        log = logging.getLogger("RemoteScripting.NodeList").info
        log("Error donwloading PlanetLab node list from plc API: %s",
            traceback.format_exc().splitlines()[-1])
        return node_list.splitlines()

    # get hostname for these nodes
    # Useful other fields: boot_state, site_id, last_contact
    # GetSites (auth, site_filter, return_fields)--> longitude , latitude


def getIP_fromDNS(hostname):
    try:
        ret = socket.gethostbyname(hostname)
    except socket.gaierror:
        ret = None
    return ret


def is_valid_ip(ip):
    numOfSegments = 0
    for segment in ip.split("."):
        numOfSegments += 1
        if not segment.isdigit() or int(segment) > 255:
            return False
    if numOfSegments != 4:
        return False
    return True


def ping(hostname, silent=True):
    try:
        if platform.system() == "Windows":
            return 0 == subprocess.check_call(["ping", hostname, "-n", "1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            return 0 == subprocess.check_call(["ping", "-c", "1", hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return False
    except Exception:
        if silent:
            print "Error at pinging: ", hostname
            print traceback.format_exc()
            return False
        else:
            raise RuntimeError


def is_private_ip(ip):
    # Class	Private Networks	Subnet Mask	Address Range
    # A	10.0.0.0	            255.0.0.0	10.0.0.0 - 10.255.255.255
    # B	172.16.0.0 - 172.31.0.0	255.240.0.0	172.16.0.0 - 172.31.255.255
    # C	192.168.0.0	            255.255.0.0	192.168.0.0 - 192.168.255.255
    parts = str(ip).split(".")
    if parts[0] == "10":
        return True
    if parts[0] == "172" and int(parts[1]) >= 16 and int(parts[1]) < 32:
        return True
    if parts[0] == "192" and parts[1] == "168":
        return True

#=================================================
# Functions used to handle
# all the PlanetLab nodes.


def install_iperf(con):
    cmd_install = "sudo yum install -y iperf"
    con.runCommand(cmd_install, timeout=25)


def check_iperf(node):
    log_id = str(node).replace(".", "_") + ".checkIperf"
    log = logging.getLogger().getChild(log_id).info
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
        outp, err = con.runCommand(cmd_test)
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
        install_iperf(con)
    except Exception:
        log("Installation failed: " + traceback.format_exc())
        return "install failed: " + \
               traceback.format_exc().splitlines()[-1]

    try:
        outp, err = con.runCommand(cmd_test)
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
    log = logging.getLogger("test_os"+node_ip.replace(".", "_")).info
    cmd = "cat /etc/issue"
    # uname -r --> gives some more inforamtion about kernel and architecture
    node = {"ip": node_ip}

    log("connect to: "+ node_ip)
    con = Connection(node["ip"])
    con.connect()

    node["online"] = con.online

    if con.error is not None:
        node["error"] = con.errorTrace.splitlines()[-1]
        log("connection error: "+ node_ip+ " --: "+ node["error"])
        return node

    log("connection succesfull: " + node_ip)
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


def scan_iperf_installations(slice_name, used_threads=200):
    print "get node list"
    nodes = getPlanetLabNodes(slice_name)

    print "start scanning on %d threads" % (used_threads)
    results = utils.thread_map(install_iperf, nodes, used_threads)
    # results = proc_map(install_iperf, nodes, used_threads)

    print "--------------------"
    c = Counter(results)
    print "Results:"

    stats = {"date": lib.get_date(), "time": lib.get_time()}
    for item in c.most_common():
        stats[item[0]] = item[1]

    print json.dumps(stats, indent=2)

    filename = "results/installations.json"
    os.makedirs(os.path.dirname(filename))
    with open(filename, "w") as f:
        f.write(json.dumps(stats, indent=2))


def scan_os_types(used_threads=200):
    log = logging.getLogger("scan_os").info

    log("get planet lab ip list")
    node_ips = getPlanetLabNodes(slice_name)

    log("start scanning them ")
    nodes = utils.thread_map(testOs, node_ips, used_threads)

    log("write out the results")
    with open("results/scan.json", "w") as f:
        f.write(json.dumps(nodes))

    log("create statistics")
    online = reduce(lambda acc, new:
                    acc + 1 if new["online"] else acc,
                    nodes, 0)
    log("Online nodes: %d", online)

    error = reduce(lambda acc, new:
                   acc + 1 if new.has_key("error")
                              and new["error"] != "offline"
                   else acc,
                   nodes, 0)
    log("Occured errors: %d", error)


def get_scan_statistic(filename="results/scan.json"):
    with open(filename, "r") as f:
        nodes = json.loads(f.read())
        errors = Counter()
        outp = Counter()
        offline = 0
        online = 0
        error = 0
        succeed = 0
        for node in nodes:
            if not node["online"]:
                offline += 1
                continue
            online += 1
            if node.has_key("error") and node["error"] != "offline":
                errors[node["error"]] += 1
                error += 1
            else:
                outp[node["outp"]] += 1
                succeed += 1

        print "Online count: ", online
        print "Offline count: ", offline
        print "Error count: ", error
        print "Succeed count: ", succeed, "\n"

        for type, count in errors.most_common(len(errors)):
            print "Error count:%d\n\t%s" % (count, type)

        for type, count in outp.most_common(len(outp)):
            print "Output count:%d\n\t%s" % (count, type)


node_list = """int-pl2.ise.eng.osaka-u.ac.jp
plab2.psgtech.ac.in
planet-lab.iki.rssi.ru
planetlab04.uncc.edu
pl5.planetlab.uvic.ca
pllab1.kamgu.ru
datacomngn.cnu.ac.kr
planetlab1.ias.csusb.edu
planetlab2.dtc.umn.edu
planetlab-01.cs.angelo.edu
planetlab1.nileu.edu.eg
planetlab3.gmf.ufcg.edu.br
charon.cs.binghamton.edu
planetlab01.erin.utoronto.ca
planetlab1.homelinux.org
pllab2.kamgu.ru
pl1.bit.uoit.ca
planetlab-1a.ics.uci.edu
of-planet5.stanford.edu
mlab1.gr-ix.gr
node1.planetlab.etl.luc.edu
planetlab2.simula.no
planetlab02.erin.utoronto.ca
deimos.cecalc.ula.ve
planetlabnode-2.docomolabs-usa.com
plab1.psgtech.ac.in
csplanet2.ncat.edu
int-pl1.ise.eng.osaka-u.ac.jp
planetlab03.uncc.edu
planetlab1.engr.ccny.cuny.edu
csplanet1.ncat.edu
planetlab1.cnu.ac.kr
planetlab3.cs.duke.edu
planetlab1.rdfrancetelecom.com
planetlab2.rdfrancetelecom.com
planetlab1.iitr.ernet.in
planetlab1.swidnik.rd.tp.pl
uw1.accretive-dsl.nodes.planet-lab.org
planetlab2.cse.nd.edu
planetlab2.cse.msu.edu
planetlab2.cs.duke.edu
pl1.dce.edu
pl3.coep.org.in
pl4.coep.org.in
planetlab-1.rml.ryerson.ca
planetlab0.ias.csusb.edu
planetlab-02.kyushu.jgn2.jp
planetlab-01.kyushu.jgn2.jp
planetlab1.gdansk.rd.tp.pl
planetlab2.gdansk.rd.tp.pl
planetlab1.poznan.rd.tp.pl
planetlab2.poznan.rd.tp.pl
planetlab1.nowogrodzka.rd.tp.pl
planetlab5.cs.duke.edu
planetlab-01.naist.jp
vayu.iitd.ernet.in
planetlab-04.naist.jp
planetlab-2.rml.ryerson.ca
pl2.ernet.in
planetlab2.iin-bit.com.cn
planetlab3.piotrkow.rd.tp.pl
planetlab3.poznan.rd.tp.pl
planetlab4.poznan.rd.tp.pl
planetlab2.lublin.rd.tp.pl
planetlab1.lublin.rd.tp.pl
planet-2.utn.edu.ar
pl1.cewit.stonybrook.edu
pli1-br-3.hpl.hp.com
planetlab2.kreonet.net
pli2-br-2.hpl.hp.com
planetlab2.iii.u-tokyo.ac.jp
planetlab1.ece.ucdavis.edu
pli1-br-2.hpl.hp.com
pli2-br-1.hpl.hp.com
planetlab2.cs.unb.ca
planetlab1.cs.unb.ca
pli1-tlnx.hpl.hp.com
planetlab1.cs.duke.edu
pluto.cs.binghamton.edu
planetlab2.engr.ccny.cuny.edu
planetlab2.iitb.ac.in
planetlab1.iitb.ac.in
planetlab1.lsd.ufcg.edu.br
opal.cnu.ac.kr
planetlab1.aub.edu.lb
planetlab2.aub.edu.lb
planetlab2.lsd.ufcg.edu.br
planet1.cdacb.ernet.in
planet2.cdacb.ernet.in
planetlab1.iiitb.ac.in
planetlab1.kreonet.net
planetlab2.iiitb.ac.in
pl2.cewit.stonybrook.edu
planetlab1.cs.wayne.edu
planet2.scs.cs.nyu.edu
planetlab-02.naist.jp
planetlab2.olsztyn.rd.tp.pl
planetlab1.it.uts.edu.au
planetlab2.it.uts.edu.au
planetlab1.cs.uchicago.edu
planetlab2.cs.uchicago.edu
planetlab1.uc.edu
planetlab2.uc.edu
planetlab1.csail.mit.edu
planetlab3.csail.mit.edu
planetlab2.csail.mit.edu
planetlab-03.naist.jp
planetlab-1.unk.edu
planetlab-2.unk.edu
mlab3.gr-ix.gr
ks.measurementlab.net
planetlab-1.vuse.vanderbilt.edu
planetlab-2.vuse.vanderbilt.edu
node1.planetlab.uprr.pr
node2.planetlab.uprr.pr
planetlab2.piotrkow.rd.tp.pl
planetlab1.piotrkow.rd.tp.pl
planetlab-3.ics.uci.edu
pl4.planetlab.uvic.ca
planetlab-04.cs.princeton.edu
pl2.bit.uoit.ca
planetlab1.n.info.eng.osaka-cu.ac.jp
planetlab2.n.info.eng.osaka-cu.ac.jp
node1.planet-lab.titech.ac.jp
node3.planet-lab.titech.ac.jp
node4.planet-lab.titech.ac.jp
planetlab3.n.info.eng.osaka-cu.ac.jp
pn1-planetlab.huawei.com
pn2-planetlab.huawei.com
node0.planetlab.etl.luc.edu
planetlab1.keldysh.ru
planetlab2.keldysh.ru
planetlab1.cs.dartmouth.edu
planetlab2.cs.dartmouth.edu
planetlab1.simula.no
itchy.cs.uga.edu
scratchy.cs.uga.edu
planetlab-1.ece.iastate.edu
mnc2.pusan.ac.kr
planetlab1.iin-bit.com.cn
lab1.asmdba.com
agni.iitd.ernet.in
planetlab2.nileu.edu.eg
planetlab1.cse.msu.edu
planetlabnode-1.docomolabs-usa.com
mlab2.gr-ix.gr
mnc1.pusan.ac.kr
planetlab2.iitr.ernet.in
fobos.cecalc.ula.ve
cs744.cs.nthu.edu.tw
planetlab3.cesnet.cz
pli1-pa-1.hpl.hp.com
planetlab1.postel.org
plnode02.cs.mu.oz.au
planetlab1.csres.utexas.edu
planetlab1.cs.columbia.edu
planetlab2.cs.umass.edu
planetlab2.nowogrodzka.rd.tp.pl
planetlab1.dtc.umn.edu
planet1.cc.gt.atl.ga.us
kupl2.ittc.ku.edu
planetlab2.koganei.itrc.net
planetlab1.cse.nd.edu
planetlab2.pop-ce.rnp.br
orbpl1.rutgers.edu
netapp6.cs.kookmin.ac.kr
planet-lab1.cs.ucr.edu
planetlab4.georgetown.edu
planetlab2.tmit.bme.hu
planetlab-1.cs.colostate.edu
planetlab1.cnds.jhu.edu
planetlab2.netmedia.gist.ac.kr
netapp7.cs.kookmin.ac.kr
pl1.cs.unm.edu
pl2-higashi.ics.es.osaka-u.ac.jp
planetlab-01.ece.uprm.edu
planetlab-2a.ics.uci.edu
planet0.jaist.ac.jp
planet1.jaist.ac.jp
planetlab03.cs.washington.edu
server1.planetlab.iit-tech.net
planet2.cc.gt.atl.ga.us
planetlab-12.e5.ijs.si
planet3.cc.gt.atl.ga.us
planetlab0.otemachi.wide.ad.jp
planetlab1.science.unitn.it
planetlab4.cs.duke.edu
planetlab5.cs.cornell.edu
planetlab6.cs.cornell.edu
planetlab1.fit.vutbr.cz
planetlab-2.imperial.ac.uk
planetlab-2.cs.unibas.ch
planetlab1.thlab.net
mlabtest.cs.princeton.edu
planetlab2.eas.asu.edu
pub1-s.ane.cmc.osaka-u.ac.jp
planetlab1.polito.it
planetlab-node-02.ucd.ie
planet2.colbud.hu
planetlab1.hiit.fi
planetlab1.csie.nuk.edu.tw
pl1.ccsrfi.net
mars.planetlab.haw-hamburg.de
vn4.cse.wustl.edu
planetlab4.williams.edu
planetlab8.millennium.berkeley.edu
planetlab2.bgu.ac.il
host4-plb.loria.fr
planetlab-4.dis.uniroma1.it
ttu2-1.nodes.planet-lab.org
planetlab-um00.di.uminho.pt
planetlab2.umassd.edu
pl01.comp.polyu.edu.hk
planetlab0.ucsc.cmb.ac.lk
planetlab02.cnds.unibe.ch
planetlab2.hust.edu.cn
pl3.cs.unm.edu
planet-plc-5.mpi-sws.org
planetlab2.ionio.gr
planet-plc-6.mpi-sws.org
planet1.cs.rochester.edu
planetlab1.cs.du.edu
planetlab2.jcp-consult.net
planetlab2.cs.du.edu
planetlab1.unr.edu
pl1.yonsei.ac.kr
pl2.yonsei.ac.kr
planetlab2.ie.cuhk.edu.hk
gschembra4.diit.unict.it
planetlab1.willab.fi
planetlab02.uncc.edu
planetlab2.cs.wayne.edu
plgmu1.ite.gmu.edu
plab4.ple.silweb.pl
ple1.dmcs.p.lodz.pl
planetlab2.xeno.cl.cam.ac.uk
planetlab1.u-strasbg.fr
pl1.uni-rostock.de
planetlab01.tkn.tu-berlin.de
onelab-2.fhi-fokus.de
pl2.ccsrfi.net
planetlab-1.cs.unibas.ch
planck228ple.test.ibbt.be
evghu12.colbud.hu
planetlab-1.ing.unimo.it
planetlab1.elet.polimi.it
pl2.eecs.utk.edu
plab1.cs.ust.hk
planetlab-3.iscte.pt
uoepl1.essex.ac.uk
planetlab-1.scie.uestc.edu.cn
planetlab1.iii.u-tokyo.ac.jp
planetlab1.eecs.northwestern.edu
planet1.inf.tu-dresden.de
planetlab2.eecs.northwestern.edu
planetlab1.poly.edu
host3-plb.loria.fr
righthand.eecs.harvard.edu
planetlab3.csres.utexas.edu
planetlab02.ethz.ch
planetlab2.cis.upenn.edu
ait05.us.es
planet1.cs.huji.ac.il
orbpl2.rutgers.edu
planetlab2.csee.usf.edu
planetlab-2.cs.colostate.edu
pli1-pa-2.hpl.hp.com
planetlab-1.iscte.pt
planetlab2.cyfronet.pl
planetlab02.cs.washington.edu
planetlab2.eecs.wsu.edu
csplanetlab4.kaist.ac.kr
planetlab5.csail.mit.edu
planetlab1.inf.ethz.ch
planetlab1.byu.edu
planetlab2.eecs.umich.edu
planetlab1.informatik.uni-goettingen.de
planetlab2.di.unito.it
planetlab2.citadel.edu
planet-plc-4.mpi-sws.org
lim-planetlab-2.univ-reunion.fr
node2.planetlab.uni-luebeck.de
orval.infonet.fundp.ac.be
planetlab1.ifi.uio.no
planetlab1.tmit.bme.hu
evghu13.colbud.hu
merkur.planetlab.haw-hamburg.de
inriarennes2.irisa.fr
planetlab2.hiit.fi
iraplab2.iralab.uni-karlsruhe.de
planetlab-2.infotech.monash.edu.my
planetlab5.ie.cuhk.edu.hk
planetlab1.uc3m.es
planetlab01.ethz.ch
evghu11.colbud.hu
planetlab1.buaa.edu.cn
planetlab1.mini.pw.edu.pl
planetlab1.informatik.uni-wuerzburg.de
onelab7.iet.unipi.it
evghu5.colbud.hu
chronos.disy.inf.uni-konstanz.de
planet2.l3s.uni-hannover.de
evghu2.colbud.hu
planetlab2.aston.ac.uk
onelab11.pl.sophia.inria.fr
marie.iet.unipi.it
planetlab1.urv.cat
pierre.iet.unipi.it
planetlab2.uc3m.es
planet-lab3.uba.ar
dannan.disy.inf.uni-konstanz.de
planetlab1.hust.edu.cn
planetlab2.fct.ualg.pt
anateus.ipv6.lip6.fr
evghu7.colbud.hu
planetlab2.dit.upm.es
planetlab2.willab.fi
chimay.infonet.fundp.ac.be
evghu8.colbud.hu
pl2.prakinf.tu-ilmenau.de
planetlab2.u-strasbg.fr
planetlab1.cs.aueb.gr
planck249ple.test.iminds.be
empusa.ipv6.lip6.fr
planetlab-03.cs.princeton.edu
planetlab2.montefiore.ulg.ac.be
peeramidion.irisa.fr
ple2.tu.koszalin.pl
planetlabeu-2.tssg.org
prometeusz.we.po.opole.pl
evghu1.colbud.hu
onelab10.pl.sophia.inria.fr
planetlab-node3.it-sudparis.eu
evghu6.colbud.hu
plnode-04.gpolab.bbn.com
planetlab1.cyfronet.pl
planetlab-2.scie.uestc.edu.cn
planetlab1.tlm.unavarra.es
planetlab-coffee.ait.ie
evghu10.colbud.hu
evghu4.colbud.hu
evghu14.colbud.hu
planetlabpc1.upf.edu
planetlab-2.di.fc.ul.pt
planetlab1.imp.fu-berlin.de
planetlab3.cs.cornell.edu
planetlab4.cs.cornell.edu
host3.planetlab.informatik.tu-darmstadt.de
plab2.create-net.org
node2pl.planet-lab.telecom-lille1.eu
planetlab1.pop-ce.rnp.br
planetlab2.exp-math.uni-essen.de
planetlab2.esprit-tn.com
evghu9.colbud.hu
vicky.planetlab.ntua.gr
planetlab-2.iscte.pt
onelab4.warsaw.rd.tp.pl
planetlab-js1.cert.org.cn
planetlab1.unl.edu
ple5.ipv6.lip6.fr
mlc1.measurementlab.net
mlc2.measurementlab.net
planetlab-1.cs.ucy.ac.cy
planet-lab-node1.netgroup.uniroma2.it
planetlab2.mini.pw.edu.pl
pl1.bell-labs.fr
planet2.servers.ua.pt
planetlab-2.fhi-fokus.de
planetlab01.cs.tcd.ie
planetlab1.ics.forth.gr
planetlab2.tlm.unavarra.es
planetlab-1.research.netlab.hut.fi
planet02.hhi.fraunhofer.de
onelab3.warsaw.rd.tp.pl
planetlab2.iiitd.edu.in
planetlab-2.research.netlab.hut.fi
planetlab1.pop-mg.rnp.br
planetlab2.ics.forth.gr
planetlab2.upc.es
planetlab1.xeno.cl.cam.ac.uk
planetlab2.unineuchatel.ch
planetlab3.ucsd.edu
planetlab1.s3.kth.se
planetlab-4.iscte.pt
planet2.unipr.it
planetlab1.fri.uni-lj.si
planetlab1.nrl.eecs.qmul.ac.uk
planetlab-4.cs.ucy.ac.cy
wlab02.pl.sophia.inria.fr
planetlab1.exp-math.uni-essen.de
planetlab1.cs.uoi.gr
planetlab2.rd.tut.fi
planetlab2.utt.fr
planetlab04.cnds.unibe.ch
planetlab2.informatik.uni-erlangen.de
planet1.itc.auth.gr
ple1.ait.ac.th
planet-plc-3.mpi-sws.org
planetlab2.ci.pwr.wroc.pl
host1.planetlab.informatik.tu-darmstadt.de
onelab3.info.ucl.ac.be
planetlab1.utt.fr
ple2.cesnet.cz
planetlab2.imp.fu-berlin.de
planetlab-3.imperial.ac.uk
planetlab1.informatik.uni-erlangen.de
planetlab2.wiwi.hu-berlin.de
planetlab-1.fhi-fokus.de
planetlab1.eurecom.fr
ple4.ipv6.lip6.fr
planetlab2.csg.uzh.ch
pl1.prakinf.tu-ilmenau.de
planetlab2.fri.uni-lj.si
rochefort.infonet.fundp.ac.be
onelab2.info.ucl.ac.be
planet1.colbud.hu
plab1.ple.silweb.pl
gschembra3.diit.unict.it
planetlab-node1.it-sudparis.eu
pandora.we.po.opole.pl
planetlab-1.infotech.monash.edu.my
dfn-ple1.x-win.dfn.de
planetlab1.di.fct.unl.pt
planetlab2.nrl.eecs.qmul.ac.uk
node1.planetlab.uni-luebeck.de
ampelos.ipv6.lip6.fr
planetlab-um10.di.uminho.pt
dplanet2.uoc.edu
planetlab13.millennium.berkeley.edu
dschinni.planetlab.extranet.uni-passau.de
planetlab1.wiwi.hu-berlin.de
planetlab2.cs.uit.no
planetlab2.s3.kth.se
planetlab1.ru.is
planck250ple.test.iminds.be
planetlab1.csg.uzh.ch
ple3.ipv6.lip6.fr
plab-2.diegm.uniud.it
planetlab3.net.in.tum.de
planetlab2.sics.se
planetlab-4.imperial.ac.uk
146-179.surfsnel.dsl.internl.net
planetlab02.dis.unina.it
planetlab1.upc.es
planetlab2.netlab.uky.edu
prata.mimuw.edu.pl
pl2.uni-rostock.de
planet2.inf.tu-dresden.de
planetlab1.jcp-consult.net
planetlab01.dis.unina.it
planetlab3.cs.st-andrews.ac.uk
planetlab1.di.unito.it
planetlab2.eecs.jacobs-university.de
onelab6.iet.unipi.it
plab-1.diegm.uniud.it
planetlab2.cs.aueb.gr
planetlab1.sics.se
planetlab3.hiit.fi
dplanet1.uoc.edu
pl1.tailab.eu
planet01.hhi.fraunhofer.de
planetlab2.ru.is
planetlab2.polito.it
planetlab1.ci.pwr.wroc.pl
aladdin.planetlab.extranet.uni-passau.de
planetlab-3.cs.ucy.ac.cy
planetlab2.cs.uoi.gr
planet1.elte.hu
planetlab1.diku.dk
planet1.servers.ua.pt
planet1.scs.stanford.edu
planetlab4.hiit.fi
plab1.create-net.org
ricepl-1.cs.rice.edu
planetlab1.aston.ac.uk
ple02.fc.univie.ac.at
pl1.csl.utoronto.ca
planetlab1.montefiore.ulg.ac.be
planetlab-1.cmcl.cs.cmu.edu
planetlab-1.di.fc.ul.pt
planet2.itc.auth.gr
planetlabeu-1.tssg.org
itchy.comlab.bth.se
planetlab1.rd.tut.fi
planetlab2.csres.utexas.edu
planetlab-13.e5.ijs.si
planetlab1.cs.cornell.edu
planetlab2.science.unitn.it
plnode01.cs.mu.oz.au
planet1.scs.cs.nyu.edu
lefthand.eecs.harvard.edu
planetlab3.cslab.ece.ntua.gr
planetlab1.unineuchatel.ch
planetlab2.um.es
ple1.cesnet.cz
planet1.l3s.uni-hannover.de
planetlab1.cis.upenn.edu
planetlab2.postel.org
ricepl-2.cs.rice.edu
planetlab1.eecs.umich.edu
kupl1.ittc.ku.edu
pl002.ece.upatras.gr
uoepl2.essex.ac.uk
planetlab3.cs.columbia.edu
planetlab2.cs.uiuc.edu
planetlab1.cs.uiuc.edu
planetlab1.koganei.itrc.net
planetlab1.fct.ualg.pt
planet2.elte.hu
planetlab2.iis.sinica.edu.tw
planetlab-1.cse.ohio-state.edu
planetlab1.cs.purdue.edu
ple01.fc.univie.ac.at
planetlab-2.man.poznan.pl
planetlab2.upm.ro
lim-planetlab-1.univ-reunion.fr
planetlab-02.ece.uprm.edu
planetlab4.cs.uiuc.edu
planetlab2.pop-mg.rnp.br
aguila1.lsi.upc.edu
planetlab3.upc.es
onelab-1.fhi-fokus.de
planetlab-1.usask.ca
planetlab-2.usask.ca
planetlab2.eee.hku.hk
planetlab1.eecs.jacobs-university.de
planetlab-2.cmcl.cs.cmu.edu
planetlab2.pjwstk.edu.pl
planetlab1.sfc.wide.ad.jp
planetlab2.sfc.wide.ad.jp
planet2.zib.de
planetlab1.esprit-tn.com
planck227ple.test.ibbt.be
planetlab1.uta.edu
planetlab1.cesnet.cz
planetlab-js2.cert.org.cn
planetlab3.netmedia.gist.ac.kr
planetlab1.ucsd.edu
planetlab-3.dis.uniroma1.it
planetlab2.informatik.uni-wuerzburg.de
scratchy.comlab.bth.se
planetlab3.di.unito.it
planetlab4.csail.mit.edu
planetlab2.singaren.net.sg
planetlab-1.imperial.ac.uk
planetlab4.ie.cuhk.edu.hk
planetlab1.dit.upm.es
planetlab1.netlab.uky.edu
planetlab1.ionio.gr
pli1-pa-3.hpl.hp.com
planetlab1.pjwstk.edu.pl
planetlab2.urv.cat
planetlab2.utep.edu
planetlab04.cs.washington.edu
planetlab1.net.in.tum.de
planetlab4.inf.ethz.ch
planetlab2.engr.uconn.edu
planet-lab2.ufabc.edu.br
planetslug4.cse.ucsc.edu
planetlab1.iis.sinica.edu.tw
planetlab1.just.edu.jo
planetlab4.singaren.net.sg
planetlab1.utep.edu
planetlab-02.vt.nodes.planet-lab.org
planetlab3.cs.uoregon.edu
planetlab14.millennium.berkeley.edu
pl2.bell-labs.fr
planetlab-1.man.poznan.pl
planetlab-1.tagus.ist.utl.pt
planetlab2.tamu.edu
planetlab2.cs.vu.nl
iraplab1.iralab.uni-karlsruhe.de
planetlab-2.sjtu.edu.cn
plgmu4.ite.gmu.edu
f20bootcd.cs.princeton.edu
planetlab1.cs.stevens-tech.edu
nw142.csie.ncu.edu.tw
pl2.6test.edu.cn
planetlab4.rutgers.edu
planetlab4.netmedia.gist.ac.kr
recall.snu.ac.kr
planetlab1.tsuniv.edu
planetlab2.buaa.edu.cn
planetlab2.tsuniv.edu
planetlab2.clemson.edu
planetlab2.cqupt.edu.cn
planetlab2.eurecom.fr
planetlab3.xeno.cl.cam.ac.uk
planetlab1.iitkgp.ac.in
planetlab2.iitkgp.ac.in
pl2.cs.unm.edu
planetlab01.alucloud.com
plnodeb.plaust.edu.cn
planetlab2.ucsd.edu
planetlab1.virtues.fi
planetlab-2.ing.unimo.it
planetlab1.um.es
planetlab5.goto.info.waseda.ac.jp
planetlab1.mnlab.cti.depaul.edu
planet-plc-1.mpi-sws.org
planet-plc-2.mpi-sws.org
planet4.cc.gt.atl.ga.us
planetlab03.cnds.unibe.ch
planetlab2.rutgers.edu
utet.ii.uam.es
plab2.nec-labs.com
planetlab-1.ssvl.kth.se
sybaris.ipv6.lip6.fr
pl3.sos.info.hiroshima-cu.ac.jp
pl4.sos.info.hiroshima-cu.ac.jp
ops.ii.uam.es
planetlab2-santiago.lan.redclara.net
pl1snu.koren.kr
planetlab4.warsaw.rd.tp.pl
planetlab02.sys.virginia.edu
planet-lab1.ufabc.edu.br
plab3.nec-labs.com
planetlab2.cesnet.cz
planetlab1.extern.kuleuven.be
kc-sce-plab2.umkc.edu
plab1.engr.sjsu.edu
plab2.engr.sjsu.edu
onelab2.warsaw.rd.tp.pl
planetlab1.otemachi.wide.ad.jp
planetlab0.dojima.wide.ad.jp
planetlab1.dojima.wide.ad.jp
planetlab1.singaren.net.sg
planetlab2.research.nicta.com.au
planetlab2.utdallas.edu
planetlab4.postel.org
planetlab6.csail.mit.edu
planetlab-node-01.ucd.ie
planetlab-01.kusa.ac.jp
planetlab-02.kusa.ac.jp
planetlab1.cs.ubc.ca
csplanetlab3.kaist.ac.kr
ple2.ait.ac.th
ait21.us.es
planetlab2.cs.ubc.ca
planetlab-2.imag.fr
planetlab2.inf.ethz.ch
planetlab3.mini.pw.edu.pl
planetlab4.mini.pw.edu.pl
planetlab1.eas.asu.edu
planetlab4.flux.utah.edu
planetlab5.flux.utah.edu
pub2-s.ane.cmc.osaka-u.ac.jp
planetlab1.citadel.edu
planetlab1.arizona-gigapop.net
planetlab1-santiago.lan.redclara.net
planetlab2-saopaulo.lan.redclara.net
planetlab1-buenosaires.lan.redclara.net
planetlab2-buenosaires.lan.redclara.net
planetlab1-tijuana.lan.redclara.net
planetlab2-tijuana.lan.redclara.net
planetlab2.byu.edu
planetlab1.upm.ro
mercury.silicon-valley.ru
plab-1.sinp.msu.ru
venus.silicon-valley.ru
plab-2.sinp.msu.ru
planetlab2.eecs.ucf.edu
planetlab01.lums.edu.pk
pli1-pa-5.hpl.hp.com
planetlab1.eecs.ucf.edu
planetlab1.williams.edu
planetlab2.williams.edu
planetlab3.williams.edu
planetlab1.netmedia.gist.ac.kr
planetlab3.inf.ethz.ch
pl1.planetlab.uvic.ca
pl3.planetlab.uvic.ca
planetlab1.comp.nus.edu.sg
planetlab2.comp.nus.edu.sg
earth.cs.brown.edu
planetlabone.ccs.neu.edu
saturn.cs.brown.edu
jupiter.cs.brown.edu
planetlab2.cs.unc.edu
planetlab16.millennium.berkeley.edu
newbootcd.cs.princeton.edu
mtuplanetlab1.cs.mtu.edu
planetx.scs.cs.nyu.edu
planetlab15.millennium.berkeley.edu
planetlab-01.bu.edu
planetlab-02.bu.edu
planetlab5.millennium.berkeley.edu
planetlab1.cs.uoregon.edu
planetlab2.virtues.fi
planet1.ku.edu.tr
planet2.ku.edu.tr
pl1.ucs.indiana.edu
cs-planetlab3.cs.surrey.sfu.ca
planetlab2.csie.nuk.edu.tw
planetlab3.csee.usf.edu
pl2.ucs.indiana.edu
planetlab1.cs.umb.edu
planetlab4.csres.utexas.edu
cs-planetlab4.cs.surrey.sfu.ca
planetlab5.csres.utexas.edu
planetlab4.csee.usf.edu
plab3.ple.silweb.pl
planetlab3.postel.org
planetlab5.williams.edu
planetlab3.wail.wisc.edu
planetlab4.wail.wisc.edu
planetlab1.utdallas.edu
planet-lab2.cs.ucr.edu
server3.planetlab.iit-tech.net
planetlab5.cs.uiuc.edu
planetlab-2.pdl.nudt.edu.cn
planetlab-1.pdl.nudt.edu.cn
plgmu3.ite.gmu.edu
plab3.eece.ksu.edu
planet-lab1.uba.ar
planet-lab2.itba.edu.ar
planetlab2.c3sl.ufpr.br
planetlab1.tamu.edu
planetlab1.bgu.ac.il
pl2.rcc.uottawa.ca
planetlab1.mta.ac.il
plab4.eece.ksu.edu
salt.planetlab.cs.umd.edu
planetlab2.cs.columbia.edu
planetlab-2.webedu.ccu.edu.tw
planetlab-01.vt.nodes.planet-lab.org
planetlab2.cs.uoregon.edu
planetlab-1.imag.fr
planetlab2.ece.ucdavis.edu
planetlab-2.tagus.ist.utl.pt
planetlab1.cs.ucla.edu
planetlab2.cs.ucla.edu
planetlab12.millennium.berkeley.edu
pl1.eecs.utk.edu
plgmu2.ite.gmu.edu
planetlab1.cs.umass.edu
planetlab2.cs.umb.edu
147-179.surfsnel.dsl.internl.net
planetlab-1.calpoly-netlab.net
planetlab3.eecs.northwestern.edu
node1.planetlab.mathcs.emory.edu
planetlab3.cs.uchicago.edu
onelab1.info.ucl.ac.be
planetlab2.mta.ac.il
pli1-br-1.hpl.hp.com
planetlab3.cse.nd.edu
planetlab2.cs.cornell.edu
node2.planetlab.mathcs.emory.edu
planetlab6.flux.utah.edu
planetlab7.flux.utah.edu
planet2.scs.stanford.edu
planetlab2.arizona-gigapop.net
planetlab6.cs.duke.edu
planetlab2.ntu.nodes.planet-lab.org
planetlab7.cs.duke.edu
planetlab5.eecs.umich.edu
planet12.csc.ncsu.edu
ebb.colgate.edu
planetlab6.cs.uiuc.edu
pl2snu.koren.kr
planetlab-04.vt.nodes.planet-lab.org
planetlab6.csee.usf.edu
planetlab-6.ece.iastate.edu
pl1.sos.info.hiroshima-cu.ac.jp
planetlab1.ucsc.cmb.ac.lk
pl2.planet.cs.kent.edu
pl2.eng.monash.edu.au
planetlab4.n.info.eng.osaka-cu.ac.jp
planetlab1.csee.usf.edu
onelab1.warsaw.rd.tp.pl
planetlab6.goto.info.waseda.ac.jp
planetlab3.cs.uiuc.edu
plab1.larc.usp.br
planetlab-1.sjtu.edu.cn
plab2.cs.ust.hk
plonk.cs.uwaterloo.ca
planetlab1.cs.otago.ac.nz
planetlab2.cs.otago.ac.nz
planetlab3.eecs.umich.edu
planetlab2.cs.ucl.ac.uk
node1.planetlab.albany.edu
node2.planetlab.albany.edu
roam1.cs.ou.edu
planetlab3.singaren.net.sg
planetlab-2.cse.ohio-state.edu
planetlab2.pop-rs.rnp.br
server2.planetlab.iit-tech.net
osiris.planetlab.cs.umd.edu
whitefall.planetlab.cs.umd.edu
planetlab2.csuohio.edu
planetlab2.cs.purdue.edu
planetlab2.poly.edu
planet-lab2.uba.ar
planetlab2.unl.edu
planetlab-2.ece.iastate.edu
pl3.planet.cs.kent.edu
planetlab-01.cs.princeton.edu
planetlab2.cnds.jhu.edu
planetlab02.cs.tcd.ie
planetlab-02.cs.princeton.edu
planetlab1.ntu.nodes.planet-lab.org
planetlab01.cs.washington.edu
planetlab-1.cs.auckland.ac.nz
planetlab-2.cs.auckland.ac.nz
pl1.rcc.uottawa.ca
pl2.pku.edu.cn
miranda.planetlab.cs.umd.edu
server4.planetlab.iit-tech.net
pnode1.pdcc-ntu.singaren.net.sg
nodea.howard.edu
planetlab-5.eecs.cwru.edu
planetlab3.arizona-gigapop.net
planetlab2.pop-pa.rnp.br
planetlab3.canterbury.ac.nz
planetlab4.canterbury.ac.nz
planetlab2.cs.stevens-tech.edu
ple1.tu.koszalin.pl
planetlab-1.elisa.cpsc.ucalgary.ca
planetlab1.pop-pa.rnp.br
plewifi.ipv6.lip6.fr
planetlab2.cs.uml.edu
planetlab-n2.wand.net.nz
planetlab1.eecs.wsu.edu
pli1-pa-4.hpl.hp.com
planetlab1.clemson.edu
planetlab-2.elisa.cpsc.ucalgary.ca
pl1.6test.edu.cn
planetlab3.rutgers.edu
planetlab-2.cs.uic.edu
cs743.cs.nthu.edu.tw
plnodea.plaust.edu.cn
flow.colgate.edu
planetlab-1.webedu.ccu.edu.tw
planetlab1.jhu.edu
planetlab2.jhu.edu
metis.mcs.suffolk.edu
pl2.sos.info.hiroshima-cu.ac.jp
planetlab-1.sysu.edu.cn
adrastea.mcs.suffolk.edu
planetlab4.cs.uoregon.edu
planetlab-2.sysu.edu.cn
planetlab3.tamu.edu
planetlab4.tamu.edu
planetlab-4.ece.iastate.edu
planetlab4.goto.info.waseda.ac.jp
planetlab1.umassd.edu
saturn.planetlab.carleton.ca
node02.verivue.princeton.edu
planetlab2.cs.pitt.edu
peeramide.irisa.fr
planetlab4.bupt.edu.cn
planetlab2.unr.edu
jupiter.planetlab.carleton.ca
planetlab1.ewi.tudelft.nl
planetlab6.millennium.berkeley.edu
planetlab7.millennium.berkeley.edu
planetlab10.millennium.berkeley.edu
planetlab11.millennium.berkeley.edu
planetlab9.millennium.berkeley.edu
kc-sce-plab1.umkc.edu
planetlab1.cqupt.edu.cn
plab1.cs.msu.ru
pl2.zju.edu.cn
planetlab2.cs.okstate.edu
planetlab1.warsaw.rd.tp.pl
nodeb.howard.edu
pl4.cs.unm.edu
pl1.cs.montana.edu
pl2.cs.montana.edu
pl221nassau0.cs.princeton.edu
planetlab02.alucloud.com
planetlab01.sys.virginia.edu
pl2.planetlab.uvic.ca
pluto.cs.brown.edu
planetlab4.cse.nd.edu
planet3.cs.ucsb.edu
planetslug5.cse.ucsc.edu
vn5.cse.wustl.edu
plab2.larc.usp.br
planetlab02.lums.edu.pk
planetlab5.csee.usf.edu
planetlab-4.eecs.cwru.edu
pl1.eng.monash.edu.au
planetlab3.cnds.jhu.edu
planetlab4.cnds.jhu.edu
pl1.planet.cs.kent.edu
planetlab1.cs.unc.edu
node01.verivue.princeton.edu
planetlab1-saopaulo.lan.redclara.net
planetlab4.cs.st-andrews.ac.uk
planetlab1.ie.cuhk.edu.hk
planet-lab4.uba.ar
planetlab1.engr.uconn.edu
planet4.cs.ucsb.edu
planetlab2.uta.edu
pli1-pa-6.hpl.hp.com
planetlab6.csres.utexas.edu
planetlab7.csres.utexas.edu
ricepl-4.cs.rice.edu
ricepl-5.cs.rice.edu
planetlab1.cs.colorado.edu
pnode2.pdcc-ntu.singaren.net.sg
planetlab2.ewi.tudelft.nl
planetlabtwo.ccs.neu.edu
planetlab-2.ssvl.kth.se
planetlab3.millennium.berkeley.edu
planetlab02.just.edu.jo
plgmu5.ite.gmu.edu
planetlab1.ecs.vuw.ac.nz
planetlab2.ecs.vuw.ac.nz
planet5.cs.ucsb.edu
planet6.cs.ucsb.edu
plnode-03.gpolab.bbn.com
inriarennes1.irisa.fr
planetlab1.millennium.berkeley.edu
ple1.zcu.cz
planetlabpc0.upf.edu
planetlab2.mnlab.cti.depaul.edu
planetlab1.cs.uml.edu
openlab01.pl.sophia.inria.fr
planetlab-n1.wand.net.nz
planetlab-2.ida.liu.se
planetlab1.een.orst.edu
planetlab2.een.orst.edu
planet1.unipr.it
mtuplanetlab2.cs.mtu.edu
planet-lab1.itba.edu.ar
planetlab3.comp.nus.edu.sg
planet11.csc.ncsu.edu
pl1.pku.edu.cn
planetlab1.plab.ege.edu.tr
planetlab-03.vt.nodes.planet-lab.org
plink.cs.uwaterloo.ca
planetlab1.eee.hku.hk
planet1.pnl.nitech.ac.jp
planetlab1.c3sl.ufpr.br
planet2.pnl.nitech.ac.jp
planet1.dsp.ac.cn
planetlab2lannion.elibel.tm.fr
planet2.dsp.ac.cn
planetlab1.aut.ac.nz
planetlab1.cs.ucl.ac.uk
planetlab2.aut.ac.nz
pl2.cs.yale.edu
pl1.cs.yale.edu
pl1.cis.uab.edu
roam2.cs.ou.edu
planetlab4.eecs.umich.edu
planet2.cs.rochester.edu
pl2.cis.uab.edu
planetlab1.cnis.nyit.edu
planetlab2.cnis.nyit.edu
pl-dccd-02.cua.uam.mx
arari.snu.ac.kr
node1pl.planet-lab.telecom-lille1.eu
planetlab02.tkn.tu-berlin.de
planet-lab-node2.netgroup.uniroma2.it
planetlab4.cslab.ece.ntua.gr
planetlab2.ustc.edu.cn
stella.planetlab.ntua.gr
planetlab-5.ece.iastate.edu
pl1-higashi.ics.es.osaka-u.ac.jp
planetlab1.cti.espol.edu.ec
planetlab2.cti.espol.edu.ec
75-130-96-12.static.oxfr.ma.charter.com
75-130-96-13.static.oxfr.ma.charter.com
pl02.comp.polyu.edu.hk
pln.zju.edu.cn
planetlab1.nakao-lab.org
planetlab2.nakao-lab.org
plab3.cs.msu.ru
ple2.ipv6.lip6.fr
planetlab4.millennium.berkeley.edu
planetlab2.tau.ac.il
pl2.tailab.eu
planetlab1.cs.okstate.edu
planetlab1.bupt.edu.cn
planetlab2.bupt.edu.cn
planetlab1.pop-rj.rnp.br
planetlab2.pop-rj.rnp.br
planetlab1.temple.edu
planetlab2.temple.edu
planetlab3.bupt.edu.cn
pl-dccd-01.cua.uam.mx
planetvs2.informatik.uni-stuttgart.de
pl001.ece.upatras.gr
planetlab-1.ida.liu.se
plab2.ple.silweb.pl
planetlab-3.ece.iastate.edu
planetlab1.acis.ufl.edu
planetlab2.acis.ufl.edu
planetlab1.cs.pitt.edu
planetlab2.thlab.net
planetlab2.plab.ege.edu.tr
planetlab05.cs.washington.edu
planetlab06.cs.washington.edu
nw144.csie.ncu.edu.tw
planetslug7.cse.ucsc.edu
planetlab2.cs.colorado.edu
planetlab4.cs.uchicago.edu
planetlab2.millennium.berkeley.edu
medea.inf.uth.gr
planetlab2.di.fct.unl.pt
planetlab1lannion.elibel.tm.fr
planetlab2.informatik.uni-goettingen.de
planet1.zib.de
planetvs1.informatik.uni-stuttgart.de
planet2.cs.huji.ac.il
planetlab2.extern.kuleuven.be
planetlab1.cs.vu.nl
planetlab-tea.ait.ie
aguila2.lsi.upc.edu
ple6.ipv6.lip6.fr
ple2.dmcs.p.lodz.pl
planetlab2.ifi.uio.no
planetlab1.tau.ac.il
roti.mimuw.edu.pl
planetlab1.pop-rs.rnp.br
planetlab3.georgetown.edu
pl2.csl.utoronto.ca
planetlab-3.cmcl.cs.cmu.edu
planetlab7.csail.mit.edu
nis-planet1.doshisha.ac.jp
nis-planet2.doshisha.ac.jp
planetlab01.uncc.edu
planetlab-2.calpoly-netlab.net
planetlab1.csuohio.edu
planetlab-1.cs.uic.edu
pl-node-0.csl.sri.com
pl-node-1.csl.sri.com
ttu1-1.nodes.planet-lab.org
planetlab1.ustc.edu.cn
plab1.nec-labs.com
planetlab1.rutgers.edu
planetlab1.research.nicta.com.au
iason.inf.uth.gr
planetlab1.cs.uit.no
planetlab2.diku.dk"""