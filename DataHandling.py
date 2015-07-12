__author__ = 'Rudolf Horvath'
__date__ = '2015.06.15'

__encoding__ = 'utf-8'
# encoding: utf-8


import sqlite3 as sql

class DataBase:

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

"""
Függvények:
 - TracerouteMeasure-ből álló lista kezelése:
  - Json file készítése
  - Beemelése SQLite adatbázisba
  - Éllisták beemelése SQLite adatbázisba
  - IP címek beolvasása
  - DNS nevek beolvasása
 - Ezen funkciók akár adatbázisból beolvasva (nyers traceroute-ból)
 - ip cím - domain név párok tárolása
 - ip cím id párosítás
 - domain név - id párosítás
"""