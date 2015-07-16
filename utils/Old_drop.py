__author__ = 'erudhor'


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
