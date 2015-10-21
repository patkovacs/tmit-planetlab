import sys
import paramiko
import subprocess
import logging
import traceback
from threading import Timer

sys.path.append("lib")
sys.path.append("lib/utils")
import lib


# Constants
rsa_file = 'ssh_needs/id_rsa'
knownHosts_file = 'ssh_needs/known_hosts'
slice_name = 'budapestple_cloud'

used_procs = 100
used_threads = 300

RUN_MEASURES = ["iperf"]  # , "traceroute"]

target1 = "152.66.244.82"
target2 = "152.66.127.81"
target_names = [target1, target2]
target_username = "mptcp"


lib.Connection.connectionbuilder = \
    lib.ConnectionBuilder(slice_name, rsa_file, None)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def main():
    pass
    continous_measuring()
    # remote.scan_os_types(used_threads)
    # remote.get_scan_statistic()


def setup_logging():
    global logger

    class MyFilter(logging.Filter):
        def filter(self, record):
            keywords = ["paramiko", "requests", "urllib3"]
            return all(map(lambda x: x not in record.name, keywords))
            # return "paramiko" not in record.name and "requests" not in record.name and "urllib3" not in record.name

    logger = paramiko.util.logging.getLogger()  # logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s][%(name)s] %(message)s', datefmt='%M.%S')
    handler.setFormatter(formatter)
    handler.addFilter(MyFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def measure_node(node, i, timeout):
    cmd = ["python", "lib/SingleMeasure.py", "-n", node]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    timer = Timer(timeout, lambda p: p.kill(), [proc])

    stderr = ""
    try:
        timer.start()
        log, stderr = proc.communicate()
    except Exception:
        log = "Reaching node %s failed (error calling process):\n%s" % (node, traceback.format_exc())
    finally:
        timer.cancel()

    if len(stderr)>0:
        log = "Reaching node %s failed (error in called process):\n%s" % (node, stderr)
    # Save log for last measure
    with open("Main.py.%d.log" % i, 'w') as f:
        f.write(log)


def continous_measuring():
    timeout = 10 # 2 minutes maximum allowed

    while True:
        nodes = lib.getPlanetLabNodes(slice_name)
        i = 0
        for node in nodes:
            i = (i + 1) % 5
            measure_node(node, i, timeout)


if __name__ == "__main__":
    main()
