import sys
import argparse
import logging
import fnmatch
import os

sys.path.append("..")
sys.path.append("utils")
import lib
from utils import setup_logging
from lib import slice_name, target1, target2, rsa_file

# Constants
# rsa_file = '../ssh_needs/id_rsa'


DEFAULT_NODE = "128.208.4.198"

lib.Connection.connection_builder = \
    lib.ConnectionBuilder(slice_name, rsa_file, None)


def search_dir(root, name, levels=0):
    matches = []
    for local_root, dirnames, filenames in os.walk(root):
        for filename in fnmatch.filter(dirnames, name):
            matches.append(os.path.join(local_root, filename))

    if len(matches) > 0:
        return matches[0]
    if levels > 0:
        return search_dir(str(os.path.join("..", root)), name, levels-1)
    return None


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


def create_measure(node, target1, target2):
    # target ip address
    trace_script = "traceroute -A -w 5.0 -q 10 %s"

    paralell_measure  = lib.ParalellMeasure()

    # Traceroute
    akt = lib.Measure(node, target1)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)

    akt = lib.Measure(node, target2)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)


    return paralell_measure


def full_mesh_measure(node):
    others = lib.get_good_nodes()
    if node in others:
        others.remove(node)

    for target in others:
        trace_script = "traceroute -A -w 5.0 -q 10 %s"

        # Traceroute
        akt = lib.Measure(node, target)
        akt.setScript("traceroute", trace_script)
        akt.run()
        data = akt.getData(False)

        if data is not None:
            lib.save_one_measure(data, db=True)


def one_measure(node):
    akt = create_measure(node, target1, target2)
    akt.startMeasure()
    akt.join()
    data = akt.getData(False)

    if data is not None:
        #lib.save_one_measure(data, db=False)
        lib.save_one_measure(data, db=True)

    full_mesh_measure(node)


def one_itg_measure(node):
    itg_check = lib.check_itg(node)
    logging.getLogger().info("D-ITG install check on node '%s': %s" % (node, itg_check))
    print node
    if not itg_check:
        return
    akt = create_paralell_itg(node, target1, target2)
    akt.startMeasure()
    akt.join()
    data = akt.getData(False)
    from DataHandling import save_one_measure

    if data is not None:
        save_one_measure(data, db=True)


def create_paralell_itg(node, target1, target2):
    trace_script = "traceroute -w 5.0 -q 10 %s"
    server_username = "mptcp"
    #duration  = 5
    paralell_measure  = lib.ParalellMeasure()

    # Traceroute
    akt = lib.Measure(node, target1)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)

    akt = lib.Measure(node, target2)
    akt.setScript("traceroute", trace_script)
    paralell_measure.addMeasure(akt, 0)

    akt=lib.ITGMeasure(node,target1, server_username)
    paralell_measure.addMeasure(akt,10)#ido soros

    akt=lib.ITGMeasure(node,target2, server_username)
    paralell_measure.addMeasure(akt,25)#ido soros

    akt=lib.ITGMeasure(node,target1, server_username)
    paralell_measure.addMeasure(akt,40)#ido parhuzamos

    akt=lib.ITGMeasure(node,target2, server_username)
    paralell_measure.addMeasure(akt,40)#ido parhuzamos

    return paralell_measure


def main():
    global logger, rsa_file

    logger = setup_logging()
    args = arg_parse()
    node = args.n

    rsa_dir = search_dir(".", "ssh_needs", 2)
    if rsa_dir is not None:
        rsa_file = str(rsa_dir)+"/id_rsa"
    else:
        logger.info("RSA key not found!")
        exit()

    lib.Connection.connection_builder = \
        lib.ConnectionBuilder(slice_name, rsa_file, None)

    one_measure(node)

    #one_itg_measure(node)


if __name__ == "__main__":
    main()
