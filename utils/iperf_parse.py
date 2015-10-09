__author__ = 'erudhor'

import re
import json

def parse_client(outp):
    #print "Client parser:\n", outp
    #RE_HEADER_INFO = re.compile(r'^Client connecting to (\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4}), (UDP|TCP) port (\d+)$')
    RE_INFO = re.compile(r'^\[ *(\d+)\]\D*(\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4})\D+(\d{1,5})\D*(\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4})\D+(\d{1,5})$')
    RE_INTERVAL_CLIENT = re.compile(r'^\[ *(\d+)\] +(\d+.\d+)- *(\d+.\d+) *(\w+) *(\d+.\d+) +(\w+) +(\d+.\d+) +([\/\w]+).*$')
    RE_SUM = re.compile(r'^\[ *(\d+)\] Sent (\d+) datagrams$')
    #RE_SERVER_REPORT_Indicator = re.compile(r'^\[ *(\d+)\] Server Report:$')
    RE_SERVER_REPORT = re.compile(r'^\[ *(\d+)\] +(\d+.\d+)- *(\d+.\d+) *(\w+) *(\d+.\d+) +(\w+) +(\d+.\d+) +([/\w]+)\s+(\d+.\d+) *(\w+)\s+(\d+)/ *(\d+).*$')

    specLine = 0
    header_line = True
    sessions = {}
    for line in outp.splitlines():
        if "------" in line:
            specLine += 1
            continue
        if specLine < 2:
            continue
        if header_line:
            header_line = False
            match_header = RE_INFO.search(line)
            session_id = match_header.group(1)
            session = {}
            session["local_ip"] = match_header.group(2)
            session["local_port"] = match_header.group(3)
            session["remote_ip"] = match_header.group(4)
            session["remote_port"] = match_header.group(5)
            session["intervals"] = []
            sessions[session_id] = session
            continue

        match_server_report = RE_SERVER_REPORT.search(line)
        if match_server_report is not None:
            session_id = match_server_report.group(1)
            report = {}
            report["from"] = match_server_report.group(2)
            report["until"] = match_server_report.group(3)
            report["time_unit"] = match_server_report.group(4)
            report["transfer"] = match_server_report.group(5)
            report["transfer_unit"] = match_server_report.group(6)
            report["bandwidth"] = match_server_report.group(7)
            report["bandwidth_unit"] = match_server_report.group(8)
            report["jitter"] = match_server_report.group(9)
            report["jitter_unit"] = match_server_report.group(10)
            report["lost"] = match_server_report.group(11)
            report["total"] = match_server_report.group(12)
            sessions[session_id]["server_report"] = report
            continue

        match_interval = RE_INTERVAL_CLIENT.search(line)
        if match_interval is not None:
            session_id = match_interval.group(1)
            interval = {}
            if "time_unit" not in sessions[session_id].keys():
                session["time_unit"] = match_interval.group(4)
                session["transfer_unit"] = match_interval.group(6)
                session["bandwidth_unit"] = match_interval.group(8)
            interval["from"] = match_interval.group(2)
            interval["until"] = match_interval.group(3)
            interval["transfer"] = match_interval.group(5)
            interval["bandwidth"] = match_interval.group(7)

            session["intervals"].append(interval)
            sessions[session_id] = session
            continue

        match_sum = RE_SUM.search(line)
        if match_sum is not None:
            session_id = match_sum.group(1)
            datagrams = match_sum.group(2)
            sessions[session_id]["datagrams"] = datagrams
            continue
    return sessions


def parse(outp):
    for line in outp.splitlines():
        if "Server listening" in line:
            return parse_server(outp)
    return parse_client(outp)


def parse_server(outp):
    #print "Server parser:\n", outp
    specLine = 0
    header_line = True
    RE_INFO = re.compile(r'^\[ *(\d+)\]\D*(\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4})\D+(\d{1,5})\D*(\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4})\D+(\d{1,5})$')
    RE_INTERVAL_SERVER = re.compile(r'^\[ *(\d+)\] +(\d+.\d+)- *(\d+.\d+) *(\w+) *(\d+.\d+) +(\w+) +(\d+.\d+) +([/\w]+)\s+(\d+.\d+) *(\w+)\s+(\d+)/ *(\d+).*$')
    RE_HEADER = re.compile(r'^\[ *ID\].*$')
    #RE_BUFFER_SIZE = re.compile(r'^UDP buffer size: +(\d+) (\w+).*$')
    sessions = {}
    session = None # No measurement found in output
    for line in outp.splitlines():
        if "------" in line:
            specLine += 1
            continue
        if specLine < 2:
            continue
        match_header = RE_INFO.search(line)
        if match_header is not None:
            session_id = match_header.group(1)
            session = {}
            session["local_ip"] = match_header.group(2)
            session["local_port"] = match_header.group(3)
            session["remote_ip"] = match_header.group(4)
            session["remote_port"] = match_header.group(5)
            session["intervals"] = []
            sessions[session_id] = session
            continue
        if RE_HEADER.search(line) is not None:
            continue
        match_interval = RE_INTERVAL_SERVER.search(line)
        if match_interval is not None:
            session_id = match_interval.group(1)
            interval = {}
            if "time_unit" not in sessions[session_id].keys():
                session["bandwidth_unit"] = match_interval.group(8)
                session["jitter_unit"] = match_interval.group(10)
                session["transfer_unit"] = match_interval.group(6)
                session["time_unit"] = match_interval.group(4)
            interval["from"] = match_interval.group(2)
            interval["until"] = match_interval.group(3)
            interval["transfer"] = match_interval.group(5)
            interval["bandwidth"] = match_interval.group(7)
            interval["jitter"] = match_interval.group(9)
            interval["lost"] = match_interval.group(11)
            interval["total"] = match_interval.group(12)
            session["intervals"].append(interval)
            sessions[session_id] = session
    return sessions
