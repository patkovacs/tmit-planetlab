__author__ = 'rudolf'

import dns.name
import dns.message
import dns.query
import dns.resolver


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

def get_as_req(ip):
    import requests
    data = {
        "action": "do_whois",
        "addr": ip,
        "family": "ipv4",
        "method_whois": "whois",
        "flag_prefix": "prefix",
        "bulk_paste": ip,
        "submit_paste": "Submit"
    }
    res = requests.get("http://asn.cymru.com/cgi-bin/whois.cgi", data)
    state = 0
    info = None
    for line in res.text.splitlines():
        if "<PRE>" in line or state > 0:
            state += 1
        if state == 4:
            info = line
            break
    if info is None:
        return None
    info.strip()
    asn = info.split("|")[0]
    if "NA" in asn:
        return None
    return int(asn)

def main():
    for ip in _get_samples():
        print ip+" - "+str(get_as_req(ip))

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