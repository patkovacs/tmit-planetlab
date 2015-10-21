import sqlite3 as sql
import os
import sys
import logging
import json
import datetime
from pymongo import MongoClient

sys.path.append("utils")
import utils
import lib


def main():

    # SingleMeasure.one_measure(getBestNodes()[0])

    from_date = datetime.date(2015, 9, 2)
    until_date = datetime.date(2015, 10, 7)

    push_results_to_db(from_date, until_date)


def save_one_measure(data, db=False):
    timeStamp = lib.get_time().replace(":", ".")[0:-3]
    filename = 'results/%s/%s/rawTrace_%s_%s.json' % (lib.get_date(), timeStamp[:2], lib.get_date(), timeStamp)

    if db:
        app_name = os.environ['OPENSHIFT_APP_NAME']
        mongo_url = os.environ['OPENSHIFT_MONGODB_DB_URL']

        client = MongoClient(mongo_url)
        db = client[app_name]
        collection = db["raw_measures"]
        collection.insert_one(json.loads(json.dumps(data)))

        collection2 = db["processed_measures"]
        collection2.insert_one(json.loads(json.dumps(read_measure(data))))


    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    with open(filename, 'w') as f:
        f.write(json.dumps(data, indent=2))


def push_results_to_db(from_date=None, until_date=None):
    if from_date is None:
        from_date = datetime.date(1970, 1, 1)
    if until_date is None:
        until_date = datetime.date(2038, 1, 1)

    results = read_results("results", from_date, until_date, process=False)
    mongo_client = MongoClient("localhost", 27017)
    db = mongo_client["dev"]
    collection = db["raw"]

    print "readed: ", len(results)

    if results is None:
        print "Error at result reading"
        return


    for doc in results:
        if doc is not None and "time" in doc.keys():
            doc["time"] = datetime.datetime.fromtimestamp(doc["time"])
        collection.insert_one(doc)

        # print "readed iperf measurements: %d" % i
        # print "readed tracerute measurements: %d" % j


class MongoDB:
    def __init__(self, ip, port, database, collection=None):
        self.client = MongoClient(ip, port)
        self.db = self.client[database]
        self.collection = self.db[collection]

    def open_collection(self, collection):
        self.collection = self.db[collection]

    def push(self, document):
        if self.collection is not None:
            self.collection.insert_one(document)


def parse_traceroute(measure, from_ip):
    outp = measure["result"]
    time = datetime.datetime.fromtimestamp(measure["time"])

    parse = utils.trparse.loads(outp, from_ip)

    prev_ip = from_ip
    end_ip = parse.dest_ip
    prev_rtt = 0
    index = 0
    links = []

    for hop in parse.hops:
        avgRTT = 0
        probLen = 0
        mainProbe = None
        for probe in hop.probes:
            if probe == "*":
                continue
            if mainProbe == None:
                mainProbe = probe.ip
            if mainProbe == probe.ip and probe.rtt != None:
                avgRTT += probe.rtt
                probLen += 1
                # probe.ip
                # probe.name
                # probe.rtt
        if mainProbe == None:
            continue
        avgRTT /= probLen
        aktIP = mainProbe
        links.append({
            "from": prev_ip,
            "to": aktIP,
            "delay": avgRTT - prev_rtt
        })
        prev_ip = aktIP
        index += 1
        prev_rtt = avgRTT

    res = {
        "from": from_ip,
        "to": end_ip,
        "datetime": time,
        "links": links
    }

    # print json.dumps(res, indent=2, default=json_util.default)

    # for ip in ip_list:
    #     print "ip: ", ip
    #     geoloc = get_geoloc(ip)
    #     asn = get_asn(ip)

    return res


def parse_iperf(measure):
    outp = measure["result"]
    return utils.iperf_parse.parse(outp)


def read_measure(measure_session):
    traceroute_results = []
    iperf_results = []
    results = []
    for measure in measure_session:
        if measure is None or "name" not in measure.keys():
            continue
        if "traceroute" in measure["name"]:
            traceroute_results.append({
                "result": parse_traceroute(measure, measure["from"]),
                "name": measure["name"]
            })
        elif "iperf" in measure["name"]:
            iperf_results.append({
                "result": parse_iperf(measure),
                "name": measure["name"]
            })

    for traceroute in traceroute_results:
        results.append(traceroute["result"])

    return results


def read_results(results_dir="results", from_date=None,
                 until_date=None, process=True):
    log = logging.getLogger("read_results").info
    results = []

    if not os.path.exists(results_dir) or\
        not os.path.isdir(results_dir):
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
        hours = os.listdir(results_dir + "/" + day)
        for hour in hours:
            dir = "%s/%s/%s" % (results_dir, day, hour)
            elements = os.listdir(dir)
            files.extend(map(lambda x: dir + "/" + x, elements))

    for to_read in files:
        try:
            with open(to_read, 'r') as f:
                akt = json.loads(f.read())
                if process:
                    results.extend(read_measure(akt))
                else:
                    results.extend(akt)

        except Exception:
            log("Error at: %s", to_read)
    return results


def get_datetime(year, month, day, hour, minute, second):
    date = datetime.date(year, month, day)
    time = datetime.time(hour, minute, second)
    return datetime.datetime.combine(date, time)


def get_epoch(date_time):
    epoch = datetime.datetime.combine(datetime.date(1970, 1, 1),
                                      datetime.time())
    return int((date_time - epoch).total_seconds())


def _get_time_dir_touple(timestamp):
    date = datetime.date.fromtimestamp(timestamp)
    hour = int((timestamp / 3600) % 24)
    minute = int((timestamp / 60) % 60)

    date_str = "{:d}.{:0>2d}.{:0>2d}".format(date.year, date.month,
                                             date.day)
    hour_str = "{:0>2d}".format(hour)
    file_mask = "{:d}.{:0>2d}.{:0>2d}_{:0>2d}.{:0>2d}"
    file_str = file_mask.format(date.year, date.month, date.day,
                                hour, minute)
    return date_str, hour_str, file_str


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
        self.c = self.con.cursor()

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
        self.c.execute('INSERT INTO "edge" VALUES(NULL, ?, ?, ?, ?, ?, ?)',
                       (fromID, toID, rtt, weight, traceID, index,))
        # con.commit()

    def get_IP_ID_db(self, ip):
        self.c.execute('SELECT "id" FROM "node" WHERE "ip"=?;', (ip,))
        res = self.c.fetchone()
        if res == None:
            return None
        else:
            return res[0]

    def getIP_from_ID(self, id):
        self.c.execute('SELECT "ip" FROM "node" WHERE "id"=?;', (id,))
        res = self.c.fetchone()
        if res == None:
            return None
        else:
            return res[0]

    def getRes(self, date):
        self.c.execute("""SELECT "start", "end", "res", "id" FROM "rawTrace"'+
                  'WHERE "online"=1 and "error"=0 and "date" LIKE ? ;""", ("%s" % (date),))
        return self.c.fetchall()

    def pushIP(self, putIP):
        if putIP == None:
            return None
        id = self.get_IP_ID_db(putIP)
        if (id == None):
            self.c.execute('INSERT INTO "node" VALUES(NULL, ?)', (putIP,))
            self.con.commit()
            id = self.get_IP_ID_db(putIP)
        return id


if __name__ == "__main__":
    main()
