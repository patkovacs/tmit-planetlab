__author__ = 'Rudolf Horvath'
__date__ = "2015.06.15"

# Imports
import paramiko
import xmlrpclib
import platform
import subprocess
import traceback
import socket

# Constants
API_URL         = 'https://www.planet-lab.eu:443/PLCAPI/'
PLC_CREDENTIALS = '../ssh_needs/credentials.private'


# Classes
class Connection:
    """ This class represents an SSH connection to a remote server.
        It can be used to run c
    """
    def __init__(self, ssh):
        self.ssh = ssh

    def runCommand(self, command, timeout=10):
        if self.ssh == None:
            raise RuntimeWarning("Connection not alive!")

        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=timeout)
        output = stdout.read()
        errors = stderr.read()
        return output, errors

    def disconnect(self):
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

        if self.knownHosts != None:
            ssh.load_host_keys(self.knownHosts)
            ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        else:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if username is None:
            username = self.slice_name

        ssh.connect(target, username=username, key_filename=self.private_key, timeout=timeout)
        return Connection(ssh)


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