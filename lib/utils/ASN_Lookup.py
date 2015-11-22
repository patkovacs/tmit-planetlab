__author__ = 'rudolf'

import dns.name
import dns.message
import dns.query
import dns.resolver
import requests
import requests.exceptions
import simplejson as json
import os.path
import lib
import socket
#from RemoteScripting import is_valid_ip, getIP_fromDNS


def _reverseIP(address):
    temp = address.split(".")
    convertedAddress = str(temp[3]) +'.' + str(temp[2]) + '.' + str(temp[1]) +'.' + str(temp[0])
    return convertedAddress


def get_asn(ip):
    url = _reverseIP(ip)+".origin.asn.cymru.com"
    asn_number = dns.resolver.query(url, 'TXT')\
        [0].strings[0].split("|")[0].strip()
    return int(asn_number)


def get_as_details(asn_number):
    url_detail = "AS"+str(asn_number)+".asn.cymru.com"
    asn_details =  dns.resolver.query(url_detail, 'TXT')[0].strings[0].split(" | ")
    asn_name_info = asn_details[4].split(" - ")

    if len(asn_name_info) < 2:
        asn_name = asn_name_info[0].split(" ")[0]
        asn_corp = asn_name_info[0].lstrip(asn_name).strip()
    else:
        asn_corp = asn_name_info[1]
        asn_name = asn_name_info[0]

    asn_corp_land = asn_corp.split(",")[-1]
    asn_corp = asn_corp.rstrip(","+asn_corp_land)
    asn_land = asn_details[1]

    asn = {
        "number": asn_number,
        "name": asn_name,
        "corporation": asn_corp,
        "corporation_land": asn_corp_land,
        "land": asn_land
    }
    return asn


def get_as(ip):
    asn = get_asn(ip)
    return get_as_details(asn)


asn_cache = dict()


def load_asn_cache(filename):
    global asn_cache

    if not os.path.exists(filename):
        print "does not exists!"
        return

    with open(filename, "r") as f:
        try:
            asn_cache.update(json.loads(f.read()))
        except Exception:
            print "exception"
            return


def save_asn_cache(filename):
    with open(filename, "w") as f:
        f.write(json.dumps(asn_cache, indent=2))




def get_as_req(ip):
    if not lib.is_valid_ip(ip):
        ip = lib.getIP_fromDNS(ip)
        if ip is None:
            print "1",
            return -2
    if lib.is_private_ip(ip):
        print "2",
        return 0
    if ip in asn_cache:
        print "o",
        return asn_cache[ip]

    data = {
        "action": "do_whois",
        "addr": ip,
        "family": "ipv4",
        "method_whois": "whois",
        "flag_prefix": "prefix",
        "bulk_paste": ip,
        "submit_paste": "Submit"
    }
    try:
        res = requests.get("http://asn.cymru.com/cgi-bin/whois.cgi", data, timeout=5)
    except requests.exceptions.ConnectionError:
        print "3",
        return None
    except socket.timeout:
        print "8",
        return None
    except requests.exceptions.ReadTimeout:
        print "9",
        return None

    state = 0
    info = None
    if "Error: no ASN or IP match on line 1." in res.text:
        print "4",
        return None

    for line in res.text.splitlines():
        if "<PRE>" in line or state > 0:
            state += 1
        if state == 4:
            info = line
            break
    if info is None:
        print "5",
        return None
    info.strip()
    asn = info.split("|")[0]
    if "NA" in asn:
        print "6",
        asn_cache.update({ip: -1})
        return -1
    try:
        asn = int(asn)
    except ValueError:
        print "7",
        return None

    asn_cache.update({ip: asn})
    print ".",
    return asn


def main():
    import time

    begin = time.time()
    for ip in _get_samples()[:8]:
        print ip+" - "+str(get_as_req(ip))
    print "First run: %.2f"%(time.time()-begin)
    begin = time.time()
    for ip in _get_samples():
        print ip+" - "+str(get_as_req(ip))
    print "Second run: %.2f"%(time.time()-begin)

def _get_samples():
    return ["128.208.4.198",
        "194.29.178.14",
        "195.113.161.84",
        "204.123.28.51",
        "193.63.75.20",
        "147.83.30.166",
        "130.104.72.213",
        "72.36.112.71",
        "159.217.144.110",
        "131.247.2.242",
        "138.246.253.3",
        "132.239.17.226",
        "194.29.178.13",
        "141.20.103.211",
        "200.19.159.34",
        "206.117.37.5",
        "142.103.2.2",
        "203.178.133.2",
        "193.137.173.218",
        "141.22.213.34",
        "195.113.161.13",
        "195.148.124.73",
        "138.246.253.1",
        "198.82.160.239",
        "130.192.157.131",
        "131.188.44.100",
        "193.136.19.29",
        "128.232.103.203",
        "128.112.139.97",
        "128.232.103.202",
        ]

if __name__ == "__main__":
    main()