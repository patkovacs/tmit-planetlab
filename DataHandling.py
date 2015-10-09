__author__ = 'Rudolf Horvath'
__date__ = '2015.06.15'

import sqlite3 as sql
import os
import time
import datetime
import logging
import json
import iperf_parse


class SQLiteDB:
    """
    Fuggvenyek:
     - TracerouteMeasure-bol allo lista kezelese:
      - Json file keszitese
      - Beemelese SQLite adatbazisba
      - ellistak beemelese SQLite adatbazisba
      - IP cimek beolvasasa
      - DNS nevek beolvasasa
     - Ezen funkciok akar adatbazisbol beolvasva (nyers traceroute-bol)
     - ip cim - domain nev parok tarolasa
     - ip cim id parositas
     - domain nev - id parositas
    """

    def __init__(self, file_name):
        self.con = sql.connect(file_name)
        self.c   = self.con.cursor()

    def close(self):
        self.con.commit()
        self.c.close()
        self.con.close()

    def fetch(self, sql_cmd, params):
        self.c.execute(sql_cmd, params)
        return self.c.fetchall()

    def fetchOne(self, sql_cmd, params):
        self.c.execute(sql_cmd, params)
        return self.c.fetchone()

    def pushLink(self, index, fromID, toID, rtt, weight, traceID):
        self.c.execute('INSERT INTO "edge" VALUES(NULL, ?, ?, ?, ?, ?, ?)', (fromID, toID, rtt, weight, traceID, index, ))
        #con.commit()

    def get_IP_ID_db(self, ip):
        self.c.execute('SELECT "id" FROM "node" WHERE "ip"=?;', (ip, ))
        res = self.c.fetchone()
        if res == None:
            return None
        else:
            return res[0]

    def getIP_from_ID(self, id):
        self.c.execute('SELECT "ip" FROM "node" WHERE "id"=?;', (id, ))
        res = self.c.fetchone()
        if res == None:
            return None
        else:
            return res[0]

    def getRes(self, date):
        self.c.execute("""SELECT "start", "end", "res", "id" FROM "rawTrace"'+
                  'WHERE "online"=1 and "error"=0 and "date" LIKE ? ;""", ("%s"%(date), ))
        return self.c.fetchall()

    def pushIP(self, putIP):
        if putIP == None:
            return None
        id = self.get_IP_ID_db(putIP)
        if(id == None):
            self.c.execute('INSERT INTO "node" VALUES(NULL, ?)', (putIP, ))
            self.con.commit()
            id = self.get_IP_ID_db(putIP)
        return id


class MongoDB:

    def __init__(self):
        pass

def _get_time_dir_touple(timestamp):
    date = datetime.date.fromtimestamp(timestamp)
    hour = int((timestamp/3600)%24)
    minute = int((timestamp/60)%60)

    date_str = "{:d}.{:0>2d}.{:0>2d}".format(date.year,date.month,
                                             date.day)
    hour_str = "{:0>2d}".format(hour)
    file_mask = "{:d}.{:0>2d}.{:0>2d}_{:0>2d}.{:0>2d}"
    file_str = file_mask.format(date.year,date.month,date.day,
                                hour, minute)
    return date_str, hour_str, file_str


def parse_traceroute(measure):
    outp = measure["result"]
    #print outp

i=0
def parse_iperf(measure):
    global i
    i+=1
    outp = measure["result"]
    return iperf_parse.parse(outp)


def read_results(results_dir="results", from_date=None, until_date=None):
    log = logging.getLogger("read_results").info

    if not os.path.exists(results_dir) or not os.path.isdir(results_dir):
        log("path does not exists")
        return

    if until_date is None:
        until_date = datetime.datetime.now().date()
    if from_date is None:
        from_date = datetime.date(1970, 1, 1)

    from_str = "{:d}.{:0>2d}.{:0>2d}".format(from_date.year,
                                             from_date.month,
                                             from_date.day)
    until_str = "{:d}.{:0>2d}.{:0>2d}".format(until_date.year,
                                              until_date.month,
                                              until_date.day)

    days = os.listdir(results_dir)
    log("until date: %s", until_date)
    log("from date: %s", from_date)

    files = []
    for day in days:
        if day < from_str or day > until_str:
            log("Not in timespan: %s", day)
            continue
        hours = os.listdir(results_dir+"/"+day)
        for hour in hours:
            dir = "%s/%s/%s"%(results_dir, day, hour)
            elements = os.listdir(dir)
            files.extend(map(lambda x: dir+"/"+x, elements))

    first = True
    for to_read in files:
        #print "reading file: ", to_read
        with open(to_read, 'r') as f:
            akt = json.loads(f.read())
        for measure in akt:
            if measure is None or "name" not in measure.keys():
                continue
            if measure["name"] == "traceroute":
                parse_traceroute(measure)
            elif "iperf" in measure["name"]:
                parse_iperf(measure)


def get_datetime(year, month, day, hour, minute, second):
    date = datetime.date(year, month, day)
    time = datetime.time(hour, minute, second)
    return datetime.datetime.combine(date, time)


def get_epoch(date_time):
    epoch = datetime.datetime.combine(datetime.date(1970, 1, 1),
                                      datetime.time())
    return int((date_time - epoch).total_seconds())


def main():
    from_date = datetime.date(2014, 9, 5)
    until_date = datetime.date(2016, 10, 2)

    read_results("results", from_date, until_date)

    print "readed iperf measurements: %d" % i

if __name__ == "__main__":
    main()