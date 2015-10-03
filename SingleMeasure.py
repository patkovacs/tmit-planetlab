from Main import *
import sys
import argparse

DEFAULT_NODE = "128.208.4.198"


def arg_parse():
    args = []
    sys.argvargs = []
    help = "text..."

    args.append(["-n", DEFAULT_NODE,
                 'dns or ip address of the target node'])

    parser = argparse.ArgumentParser(description=help)
    for arg in args:
        parser.add_argument(arg[0], default=arg[1], help=arg[2])

    return parser.parse_args()


def create_paralell_iperf(node, target1, target2):
    duration  = 5
    interval  = 1
    bandwidth = 20
    port      = 5200

    # target ip address
    trace_script = "traceroute -w 5.0 -q 3 %s"

    # ip interface - port
    iperf_server_script = 'iperf -s -B %s -u -p %d -i 1'

    # ip address - port - duration - interval - bandwidth Mbitps
    start_client_skeleton = "iperf -c %s -p %d -u -t %d -i %d -b %dm -f m -i 1"

    paralell_measure  = ParalellMeasure()

    # Traceroute
    akt = Measure(node, target1)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)

    akt = Measure(node, target2)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)

    def addIperf(paralell_measure, name, target, start, duration, bandwidth, port, interval):
        akt = Measure(target, None, "mptcp")
        akt.setScript("iperf_server_"+name, iperf_server_script % (target, port), duration+3)
        paralell_measure.addMeasure(akt, start, True, duration+2)

        akt = Measure(node, target)
        script = start_client_skeleton % (target, port, duration,
                                          interval, bandwidth)
        akt.setScript("iperf_client_"+name, script)
        paralell_measure.addMeasure(akt, start+1,)

        return paralell_measure

    def addIperf_oneBandwidth_scenario(akt_measure, name_prefix, target1_, target2_, bandwitdh_, start_time):

        # Iperf

        # Single 1
        akt_measure = addIperf(akt_measure, name_prefix+"single_1", target1_,
                                    start_time, duration, bandwitdh_, port, interval)

        # Single 2
        akt_measure = addIperf(akt_measure, name_prefix+"single_2", target2_,
                                    start_time+duration+3, duration, bandwitdh_, port, interval)

        # Paralell
        akt_measure = addIperf(akt_measure, name_prefix+"paralell_1", target1_,
                                    start_time+2*(duration+3), duration, bandwitdh_, port, interval)
        akt_measure = addIperf(akt_measure, name_prefix+"paralell_2", target2_,
                                    start_time+2*(duration+3), duration, bandwitdh_, port, interval)

        return akt_measure

    for i in range(20, 25):
        start_time = (i-20)*3*(duration+3)
        paralell_measure = addIperf_oneBandwidth_scenario(paralell_measure, "bw"+str(i),
                                                          target1, target2, i, start_time)
    #paralell_measure = addIperf(paralell_measure, "test", target1,
    #                                5, duration, bandwidth, port, interval)

    #for item in paralell_measure.measures:
    #    print item["measure"].script
    #    print item["measure"].name

    return paralell_measure


def main():
    setup_logging()
    args = arg_parse()
    node = args.n

    iperf_check = check_iperf(node)
    logger.info("Iperf install check on node '%s': %s" % (node, iperf_check))

    if "installed" not in iperf_check:
        return
    akt = create_paralell_iperf(node, target1, target2)
    akt.startMeasure()
    akt.join()
    data = akt.getData(False)
    if data is not None:
        #print data
        saveOneMeasure(data)


if __name__ == "__main__":
    main()
