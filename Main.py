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
from lib import slice_name, rsa_file, known_hosts_file

# Constants
used_procs = 100
used_threads = 50

lib.set_ssh_data(slice_name, rsa_file, known_hosts_file)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

node_len = 0


def main():
    pass

    continous_measuring()
    exit()

    if len(sys.argv) == 1:
        continous_measuring()
        return
    if sys.argv[1] == "scan":
        args = {
            "cmd": "cat /etc/issue",
            "save_result": False,
            "do_statistics": False
        }
        # nodes=None, cmd=None, stdout_proc=None, stderr_proc=None,
        #  timeout=10, save_erroneous=True,
        #  save_stdout=True, save_stderr=True,
        #  node_script=scan_script, save_result=True

        scan(**args)
        return
    if sys.argv[1] == "dev":

        return

    # remote.scan_os_types(used_threads)
    # remote.get_scan_statistic()


def scan_script(args):
    global node_len
    node_len -= 1

    ip = args["ip"]
    cmd = "cat /etc/issue"
    timeout = 10

    if "cmd" in args and args["cmd"] is not None:
        cmd = args["cmd"]
    if "timeout" in args and args["timeout"] is not None:
        timeout = args["timeout"]

    log = logging.getLogger("scan."+str(ip).replace(".","_")).info
    node = {"ip": ip}
    logging.getLogger("scan").fatal("nodes to do: %d", node_len)

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
        outp, err = con.runCommand(cmd, timeout=timeout)
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


def scan(nodes=None, cmd=None, stdout_proc=None, stderr_proc=None,
         timeout=10, save_erroneous=True, do_statistics=True,
         save_stdout=True, save_stderr=True,
         node_script=scan_script, save_result=True):
    global node_len
    log = logging.getLogger().info

    if nodes is None:
        log("get planet lab ip list")
        nodes = lib.getPlanetLabNodes(slice_name)#lib.getBestNodes()[:5]
    node_len = len(nodes)

    log("start scanning them ")
    args = {"cmd": cmd,
            "timeout": timeout}
    node_calls = [args.update(ip=ip) for ip in nodes]

    nodes = utils.thread_map(node_script,
                             node_calls, used_threads)

    if stdout_proc is not None:
        log("Run output processing")
        for node in nodes:
            node["data"] = stdout_proc(node["stdout"])

    if stderr_proc is not None:
        log("Run error processing")
        for node in nodes:
            node["error"] = stderr_proc(node["stderr"])

    log("filter not needed informations")
    if not save_erroneous:
        new_list = []
        for node in nodes:
            if "error" not in node and\
                    node["online"] == "online":
                new_list.append(node)
        nodes = new_list

    if not save_stderr:
        for node in nodes:
            node.pop("stderr", None)

    if not save_stdout:
        for node in nodes:
            node.pop("stdout", None)

    if save_result:
        log("write out the results")
        with open("results/scan.json", "w") as f:
            f.write(json.dumps(nodes))

    if do_statistics:
        log("calculate statistics")
        stats = scan_statistics(nodes)
        #print json.dumps(stats, indent=2)


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
        #nodes = lib.getBestNodes()
        i = 0
        for node in nodes:
            i = (i + 1) % 5
            measure_node(node, i, timeout)


if __name__ == "__main__":
    main()
