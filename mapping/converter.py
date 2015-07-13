__author__ = 'Rudolf'

import json

skeleton = {"type": "FeatureCollection",
            "crs": { "type": "name",
                     "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
            }

features = []

with open("city_locs_zalan.txt", "r") as f:
    index = 0
    for line in f.readlines():
        index += 1
        #if index > 21:
        #    break
        if line[0] == "#" or len(line) < 5:
            continue
        data = line.split(" ")
        ip   = data[0]
        lat  = float(data[2])
        lon  = float(data[1])
        #probes = int(data[3])
        #if probes < 30:
        #    continue
        newData = {"type": "Feature",
                  "properties": { "name": ip },
                  "geometry": { "type": "Point",
                                "coordinates": [ lat, lon ] } }
        features.append(newData)

skeleton["features"] = features
print "Number of Points: ", len(features)

with open("generated3.geojson", "w") as f:
    f.write(json.dumps(skeleton, indent=2))