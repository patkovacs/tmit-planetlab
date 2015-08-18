__author__ = 'Rudolf Horvath'
__date__ = "2015.06.15"

# Imports
import paramiko
import xmlrpclib
import platform
import subprocess
import traceback
import socket
from threading import Thread
import time
import logging
import simplejson as json


# Constants
API_URL         = 'https://www.planet-lab.eu:443/PLCAPI/'
PLC_CREDENTIALS = 'ssh_needs/credentials.private'


#=================================================
# Classes


class Connection:
    """ This class represents an SSH connection to a remote server.
        It can be used to run c
    """
    connectionbuilder = None


    def __init__(self, ip, username=None, conBuilder=None):
        if conBuilder is None:
            self.conBuilder = Connection.connectionbuilder
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
        if self.ssh == None:
            raise RuntimeWarning("Connection not alive!")

        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=timeout)
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

        if not validIP(target):
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
# Functions


def getPlanetLabNodes(slice_name):
    global PLC_CREDENTIALS, API_URL

    plc_api = xmlrpclib.ServerProxy(API_URL, allow_none=True)
    cred    = open(PLC_CREDENTIALS,'r')

    auth = { 'AuthMethod' : 'password',
             'Username' : cred.readline().split('\n')[0],
             'AuthString' : cred.readline().split('\n')[0],
    }

    # the slice's node ids
    node_ids = plc_api.GetSlices(auth, slice_name, ['node_ids'])[0]['node_ids']

    # get hostname for these nodes
    return [item["hostname"] for item in plc_api.GetNodes(auth,node_ids,['hostname'])]
    # Useful other fields: boot_state, site_id, last_contact
    # GetSites (auth, site_filter, return_fields)--> longitude , latitude


def getIP_fromDNS(hostname):
    try:
        ret = socket.gethostbyname(hostname)
    except socket.gaierror:
        ret = None
    return ret


def validIP(ip):
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