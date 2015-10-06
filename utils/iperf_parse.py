__author__ = 'erudhor'

import re
import json



class Interval:

    def __init__(self, from_time, until_time):
        self.from_time = from_time
        self.until_time = until_time

class IperfSession:

    def __init__(self, local_ip, local_port, remote_ip, remote_port):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.intervals = []

def parse(outp):
    specLine = 0
    header_line = True
    RE_INFO = re.compile(r'^\[ *(\d+)\]\D*(\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4})\D+(\d{1,5})\D*(\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4})\D+(\d{1,5})$')
    RE_INTERVAL_SERVER = re.compile(r'^\[ *(\d+)\] +(\d+.\d+)- *(\d+.\d+) *(\w+) *(\d+.\d+) +(\w+) +(\d+.\d+) +([/\w]+)\s+(\d+.\d+) *(\w+)\s+(\d+)/ *(\d+).*$')
    RE_HEADER = re.compile(r'^\[ *ID\].*$')
    session = {}
    intervals = []
    for line in outp.splitlines():
        if "------" in line:
            specLine += 1
            continue
        if specLine < 2:
            continue
        if header_line:
            header_line = False
            match_header = RE_INFO.search(line)
            session["id"] = match_header.group(1)
            session["local_ip"] = match_header.group(2)
            session["local_port"] = match_header.group(3)
            session["remote_ip"] = match_header.group(4)
            session["remote_port"] = match_header.group(5)
            continue
        if RE_HEADER.search(line) is not None:
            continue
        interval = {}
        match_interval = RE_INTERVAL_SERVER.search(line)
        if "time_unit" not in session.keys():
            session["bandwidth_unit"] = match_interval.group(8)
            session["jitter_unit"] = match_interval.group(10)
            session["transfer_unit"] = match_interval.group(6)
            session["time_unit"] = match_interval.group(4)
        #interval["id"] = match_interval.group(1)
        interval["from"] = match_interval.group(2)
        interval["until"] = match_interval.group(3)
        interval["transfer"] = match_interval.group(5)
        interval["bandwidth"] = match_interval.group(7)
        interval["jitter"] = match_interval.group(9)
        interval["lost"] = match_interval.group(11)
        interval["total"] = match_interval.group(12)
        intervals.append(interval)
    session["intervals"] = intervals
    return session
