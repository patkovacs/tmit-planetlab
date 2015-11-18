__author__ = 'Rudolf'


import requests
import simplejson as json


def get_geoloc(ip):
    # LOL security lvl 0: token=iplocation.net
    url = "https://ipinfo.io/"+str(ip)+"/json?token=iplocation.net"
    response = json.loads(requests.get(url).text)
    print response
    if response.has_key("loc"):
        loc = response["loc"].split(",")

        lat = loc[0]
        lon = loc[1]
    else:
        lat = 0
        lon = 0

    if response.has_key("country"):
        country = response["country"]
    else:
        country = ""

    if response.has_key("org"):
        asn = response["org"].split(" ")[0][2:]
    else:
        asn = ""

    if response.has_key("city") and response["city"] is not None:
        city = response["city"]
    else:
        city = ""

    res = {
        "longitude": lon,
        "latitude": lat,
        "country": country,
        "asn": asn,
        "city": city,
        "ip": ip
    }

    return res


def main():
    for ip in _get_samples():
        get_geoloc(ip)


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
