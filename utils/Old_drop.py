__author__ = 'Rudolf Horvath'



# node_lists = splitList(nodes, int(len(nodes) / used_procs))
# result_lists = proc_map(inception, node_lists, used_procs)
# results = glueList(result_lists)

def create_paralell_iperf(node, target1, target2):
    duration = 5
    interval = 1
    bandwidth = 20
    port = 5200

    # target ip address
    trace_script = "traceroute -w 5.0 -q 3 %s"

    # ip interface - port
    iperf_server_script = 'iperf -s -B %s -u -p %d -i 1'

    # ip address - port - duration - interval - bandwidth Mbitps
    start_client_skeleton = "iperf -c %s -p %d -u -t %d -i %d -b %dm -f m -i 1"

    paralell_measure = ParalellMeasure()

    # Traceroute
    akt = Measure(node, target1)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)

    def addIperf(paralell_measure, name, target, start, duration, bandwidth, port, interval):
        akt = Measure(target, None, "mptcp")
        akt.setScript("iperf_server_" + name, iperf_server_script % (target, port), duration + 3)
        paralell_measure.addMeasure(akt, start, True, duration + 2)

        akt = Measure(node, target)
        script = start_client_skeleton % (target, port, duration,
                                          interval, bandwidth)
        akt.setScript("iperf_client_" + name, script)
        paralell_measure.addMeasure(akt, start + 1, )

        return paralell_measure

    def addIperf_oneBandwidth_scenario(akt_measure, name_prefix, target1_, target2_, bandwitdh_, start_time):
        # Iperf

        # Single 1
        akt_measure = addIperf(akt_measure, name_prefix + "single_1", target1_,
                               start_time, duration, bandwitdh_, port, interval)

        # Single 2
        akt_measure = addIperf(akt_measure, name_prefix + "single_2", target2_,
                               start_time + duration + 3, duration, bandwitdh_, port, interval)

        # Paralell
        akt_measure = addIperf(akt_measure, name_prefix + "paralell_1", target1_,
                               start_time + 2 * (duration + 3), duration, bandwitdh_, port, interval)
        akt_measure = addIperf(akt_measure, name_prefix + "paralell_2", target2_,
                               start_time + 2 * (duration + 3), duration, bandwitdh_, port, interval)

        return akt_measure

    for i in range(20, 25):
        start_time = (i - 20) * 3 * (duration + 3)
        paralell_measure = addIperf_oneBandwidth_scenario(paralell_measure, "bw" + str(i), target1, target2, i,
                                                          start_time)

    # for item in paralell_measure.measures:
    #    print item["measure"].script
    #    print item["measure"].name

    return paralell_measure


def measure_iperf():
    global measures
    port = 5200
    duration = 5
    node_names = bestNodes()[:1]
    nodes = []

    logger.info("Initializing iperf measures")
    for node_name in node_names:
        nodes.append(create_paralell_iperf(node_name, target1, target2))

    logger.info("Starting measurements")
    for node in nodes:
        node.startMeasure()
        node.join()

        logger.info("-----------------------------\nMeasurement ended:")
        logger.info(node.getData())

    measures = nodes


def init():
    global measures, target_names, nodes

    # nodes = getPlanetLabNodes(slice_name)
    nodes = bestNodes()
    print "number of nodes: ", len(nodes)
    print "\tfirst node: ", nodes[0]

    # Build up the needed Measures
    for target in target_names:
        for node in nodes:  # nodes[200:300]:
            measures.append(TracerouteMeasure(node, target))


def persist():
    global results

    for measure in measures:
        data = measure.getData()
        if data is not None:
            results.append(data)

    if len(results) == 0:
        return

    # escape : to . and remove seconds
    timeStamp = getTime().replace(":", ".")[0:-3]
    filename = 'results/rawTrace_%s_%s.json' % (getDate(), timeStamp)
    with open(filename, 'w') as f:
        f.write(json.dumps(results, indent=2))

    """
    filename = 'results/rawTrace_%s_%s.txt.gzip'%(getDate(), timeStamp)
    with open(filename,'w') as f:
        blob        = json.dumps(results, indent=2)
        blob_gzip   = zlib.compress(blob, 9)
        blob_base64 = base64.b64encode(blob_gzip)
        f.write(blob_base64)
    """


def measure():
    global measures

    def connectAndMeasure(measure):
        connected = measure.connect()
        if connected:
            measure.runMeasure()
        return measure

    begin = time()
    print "runMeasurements on %d threads..." % used_threads
    measures = thread_map(connectAndMeasure, measures, used_threads)
    # workers = Pool(used_threads)
    # measures2 = workers.map(connectAndMeasure, measures)
    print "Elapsed time: %0.0f seconds" % (time() - begin)
    suceed = reduce(
        lambda acc, new:
        acc + 1 if new.error == None else acc,
        measures, 0)
    print "Succeed measures: %d" % suceed


def measure_old():
    connected = 0
    success = 0
    begin = last = time()
    tried = 0
    offline = 0
    # Run them once at a time
    for measure in measures:
        tried += 1
        succeed = measure.connect()
        if succeed:
            connected += 1
            print " - connected (",connected,")\t[tried: ", tried, "]"
            measure.runMeasure()
            if measure.error == None:
                success += 1
                print " + succeed (", success, ")"
                print " - elapsed time: %0.0f seconds"% (time() - begin)
                print " - measure time: %0.0f seconds"% (time() - last)
        else:
            print "offline - ", measure.fromIP
            offline += 1
        last = time()

    print "tried: ", len(measures)
    print "connected: ", connected
    print "succeed: ", success
    print "offline: ", offline


def test_old():
    connBuilder = ConnectionBuilder(slice_name, rsa_file, None)
    TracerouteMeasure.connection_builder = connBuilder
    target = "152.66.244.83"
    node = "pli1-pa-1.hpl.hp.com"
    measure = TracerouteMeasure(node, target)

    print "connecting"
    succeed = measure.connect()
    if succeed:
        print "connected"
        print "measure started"
        succeed = measure.runMeasure()
        print "measure ended"
        if succeed:
            print "measure succeed"
            print "result:"
            print measure.rawResult
        else:
            print "measure unsuccessful"
            print "error: ", measure.error
            print "Trace:\n", measure.errorTrace
    else:
        print "connection failure"
        print "error: ", measure.error
        print "Trace:\n", measure.errorTrace
