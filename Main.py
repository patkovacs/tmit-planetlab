import sys
import paramiko
import subprocess
import logging
import traceback
import time
from threading import Timer
import simplejson as json
from collections import Counter


sys.path.append("lib")
sys.path.append("lib/utils")
import lib
import utils


# Constants
used_procs = 100
used_threads = 20

target1 = "152.66.244.82"
target2 = "152.66.127.81"
target_names = [target1, target2]
target_username = "mptcp"

rsa_file = 'ssh_needs/id_rsa'
known_hosts_file = 'ssh_needs/known_hosts'
slice_name = 'budapestple_cloud'


lib.set_ssh_data(slice_name, rsa_file, known_hosts_file)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def main():
    pass

    if len(sys.argv) == 1:
        continous_measuring()
        return
    if sys.argv[1] == "scan":
        cmd = "uname -a"

        def proc(stdout):
            if "x86_64" in stdout:
                return "64bit"
            else:
                return "32bit"

        # @ToDo: Option to not save stdout, just data
        # @ToDo: Option to not save erroneous
        # @ToDo: Option to have a proc for stderr too?
        scan(cmd, proc)
        return

    # remote.scan_os_types(used_threads)
    # remote.get_scan_statistic()




def scan_script(args):
    ip = args[0]
    cmd = "cat /etc/issue"
    proc = None

    if len(args) > 1 and args[1] is not None:
        cmd = args[1]
    if len(args) > 2 and args[2] is not None:
        proc = args[2]

    log = logging.getLogger("scan."+str(ip).replace(".","_")).info
    node = {"ip": ip}

    log("connect to: "+ ip)
    con = lib.Connection(node["ip"])
    con.connect()

    node["online"] = con.online

    if con.error is not None:
        node["error"] = con.errorTrace.splitlines()[-1]
        node["stderr"] = con.errorTrace
        log("connection error: "+ ip+ " --: "+ node["error"])
        return node

    log("connection succesfull: " + ip)
    try:
        node["time"] = time.time()
        outp, err = con.runCommand(cmd)
    except Exception:
        stderr = traceback.format_exc()
        node["error"] = "connection error: "+stderr.splitlines()[-1]
        node["stderr"] = stderr
        return node

    if len(err) > 0:
        node["error"] = "runtime error: "+str(err).splitlines()[-1]
        node["stderr"] = str(err)
        return node

    node["stdout"] = str(outp)

    if proc is not None:
        node["data"] = proc(outp)

    return node


def scan_statistics(nodes, do_log=True, handle_stderr=False):
    log = logging.getLogger("statistics").info
    if do_log:
        log("create statistics")
    errors = Counter()
    outputs = Counter()
    error_types = Counter()
    offline = 0
    online = 0
    error = 0
    succeed = 0

    for node in nodes:
        if not node["online"]:
            offline += 1
            continue
        online += 1
        if "error" in node and node["error"] != "offline":
            error_types[node["error"]] += 1
            error += 1
            if handle_stderr and "stderr" in node:
                errors[node["stderr"]] += 1

        else:
            outputs[node["stdout"]] += 1
            succeed += 1

    errors = errors.most_common(len(errors))
    outputs = outputs.most_common(len(outputs))
    error_types = error_types.most_common(len(error_types))

    if do_log:
        log("Online count:  %d", online)
        log("Offline count: %d", offline)
        log("Erroneous count:   %d", error)
        log("Succeed count: %d", succeed)

        log("\nOutputs:")
        for type, count in outputs:
            log("Output count:%d\n\t%s", count, type)

        log("\nError types:")
        for type, count in error_types:
            log("Error type count:%d\n\t%s", count, type)

        log("\nError outputs:")
        for type, count in errors:
            log("Error output count:%d\n\t%s", count, type)

    res = {
        "online": online,
        "offline": offline,
        "succeed": succeed,
        "erroneous": error,
        "outputs": [{
                        "count": count,
                        "stdout": type
                    } for type, count in outputs],
        "error_types": [{
                        "count": count,
                        "error": type
                    } for type, count in error_types]
    }

    if handle_stderr:
        res["errors"] = [{
                            "count": count,
                            "stderr": type
                        } for type, count in errors]

    return res


def scan(cmd=None, proc=None):
    log = logging.getLogger().info

    log("get planet lab ip list")
    node_ips = lib.getBestNodes()[:5]#lib.getPlanetLabNodes(slice_name)

    log("start scanning them ")
    node_calls = [(ip, cmd, proc) for ip in node_ips]
    nodes = utils.thread_map(scan_script,
                             node_calls, used_threads)

    log("write out the results")
    with open("results/scan.json", "w") as f:
        f.write(json.dumps(nodes))

    log("calculate statistics")
    stats = scan_statistics(nodes)
    print json.dumps(stats, indent=2)


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
    timeout = 30

    while True:
        nodes = lib.getPlanetLabNodes(slice_name)
        i = 0
        for node in nodes:
            i = (i + 1) % 5
            measure_node(node, i, timeout)


if __name__ == "__main__":
    main()
