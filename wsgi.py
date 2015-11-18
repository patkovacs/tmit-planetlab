#!/usr/bin/python
import os

virtenv = os.environ['OPENSHIFT_PYTHON_DIR'] + '/virtenv/'
virtualenv = os.path.join(virtenv, 'bin/activate_this.py')
try:
    execfile(virtualenv, dict(__file__=virtualenv))
except IOError:
    pass
#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
#
import subprocess
import re
import simplejson as json
from pymongo import MongoClient
from bson.code import Code
import traceback
import datetime
import glob


def python_processes():
    # ps -A u | grep " [p]ython "
    # USER        PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
    # 6547     468363  0.1  0.0 294608 11972 ?        Sl   Oct20   1:52 python Main.py
    # 6547     225073  3.1  0.1 140544 17220 ?        S    11:54   0:00   python SingleMeasure.py -n planetlab-2.rml.ryerson.ca
    RE_PROCESS_INFO = re.compile(r'^\d+\s+(\d+)\s+([\.\d]+)\s+([]\.\d]+).*\s+([:\w]+)\s+([\d:]+)\s+(python.*)$')

    #print "Call ps aux command"
    msg = subprocess.check_output(["ps", "aux"])
    #print "Call ended: \n", msg
    processes = []
    actTime = None
    for line in msg.splitlines():
        match = RE_PROCESS_INFO.search(line)
        if "wsgi" in line:
            actTime = line
        if match is not None:
            if "wsgi" in match.group(6):
                actTime = match.group(4)
                continue
            info = {
                "pid": match.group(1),
                "cpu": match.group(2)+"%",
                "mem": match.group(3)+"%",
                "start": match.group(4),
                "time": match.group(5),
                "cmd": match.group(6)
            }
            processes.append(info)
    #print "Time: ", actTime
    return actTime, processes


def last_measure_time():
    #print "last_measure_time called"
    app_name = os.environ['OPENSHIFT_APP_NAME']
    mongo_url = os.environ['OPENSHIFT_MONGODB_DB_URL']

    #print "Connect to DB: ", mongo_url
    client = MongoClient(mongo_url)
    db = client[app_name]
    collection = db["raw_measures"]

    #print "Connected to DB!"

    map = Code("""
    function() {
    for (var idx = 0; idx < this.result.length; idx++){
        if (this.result[idx] == null){
            return;
        }
        if (isNumber(this.result[idx].time))
            emit("time", this.result[idx].time);
    }
    }""")

    reduceMax = Code("""
    function(key, times) {
    max = times[0]
    for (var idx = 0; idx < times.length; idx++) {
        if (times[idx] > max)
            max = times[idx]
    }
    return max
    }""")

    reduceMin = Code("""
    function(key, times) {
    min = times[0]
    for (var idx = 0; idx < times.length; idx++) {
        if (times[idx] < min)
            min = times[idx]
    }
    return min
    };""")

    #print "call mapreduce"
    max = collection.map_reduce(map, reduceMax, {"inline" : 1})
    min = collection.map_reduce(map, reduceMin, {"inline" : 1})

    try:
        max = float(max["results"][0]["value"])
        min = float(min["results"][0]["value"])
    except Exception:
        print traceback.format_exc()
        return {"max": 0,
                "min": 0}

    #print "call ended: max = ", max
    #print "call ended: min = ", min
    return {"max": max,
            "min": min}


def measure_outputs():
    repo_dir = os.environ['OPENSHIFT_REPO_DIR']
    logs = glob.glob1(repo_dir, "*.log")
    res = []
    if len(logs) == 0:
        res.append("No logs found!")
    else:
        for log_file in logs:
            with open(os.path.join(repo_dir, log_file), "r") as f:
                log = f.read().replace("\n", "\n\t")
                res.append("\n\n%s:\n%s"%(log_file, log))

    return "".join(res)


def homepage():
    server_time, proc_infos = python_processes()
    measurement_info = last_measure_time()

    proc_list = ""
    for proc in proc_infos:
        proc_list += "%s\n\tStarted: %s\n\tMem: %s\n\tCPU: %s\n" \
            % (proc["cmd"], proc["start"], proc["mem"], proc["cpu"])
    #proc_list = "\n".join([json.dumps(proc, indent=2) for proc in proc_infos])

    max = datetime.datetime.fromtimestamp(measurement_info["max"])
    min = datetime.datetime.fromtimestamp(measurement_info["min"])
    now = datetime.datetime.now()
    delta = int((now - max).total_seconds())

    msg = """
Server time:
    %s

Python processes:
%s

Elapsed time after last measurement:
    Days:    %d
    Hours:   %d
    Minutes: %d
    Seconds: %d

Measurement times:
    Min date: %s
    Max date: %s
    Now date: %s
    Min from epoch: %s
    Max from epoch: %s

Output log of last 5 measurements:

%s""" % \
        (server_time,
         proc_list,
         int(delta/(24*60*60)), # Days
         int((delta%(24*60*60))/(60*60)), # Hours
         int((delta%(60*60))/(60)), # Minutes
         int(delta%(60)), # Seconds
         min.isoformat("\t"),
         max.isoformat("\t"),
         now.isoformat("\t"),
         str(measurement_info["min"]),
         str(measurement_info["max"]),
         measure_outputs()
         )

    msg = msg.replace("\n", "<br>")
    msg = msg.replace(" ", "&nbsp;")
    msg = msg.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
    return msg

def application(environ, start_response):

    ctype = 'text/plain'
    if environ['PATH_INFO'] == '/health':
        response_body = "1"
    # elif environ['PATH_INFO'] == '/env':
    #     response_body = ['%s: %s' % (key, value)
    #                 for key, value in sorted(environ.items())]
    #     response_body = '\n'.join(response_body)
    else:
        ctype = 'text/html'
        response_body = homepage()

    status = '200 OK'
    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    #
    start_response(status, response_headers)
    return [response_body]

#
# Below for testing only
#
if __name__ == '__main__':
    #print homepage()
    #exit()
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8051, application)
    # Wait for a single request, serve it and quit.
    httpd.handle_request()
