__author__ = 'Rudolf'
import logging
import paramiko
import sys

def setup_logging():
    global logger

    class MyFilter(logging.Filter):
        def filter(self, record):
            keywords = ["paramiko", "requests", "urllib3"]
            return all(map(lambda x: x not in record.name, keywords))
            # return "paramiko" not in record.name and "requests" not in record.name and "urllib3" not in record.name

    logger = paramiko.util.logging.getLogger()  # logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s][%(name)s] %(message)s', datefmt='%M.%S')
    handler.setFormatter(formatter)
    handler.addFilter(MyFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
