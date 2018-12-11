#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, getopt
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
from proto_py_es_bulk import *
from scribes import *
from utils.common_logging import setup_loggers
from analyzers import *

logger = logging.getLogger("ceph_stockpile")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)


def main(): 
    setup_loggers("ceph_stockpile", logging.INFO)

    
    logger.info("Gathering cbt configuration settings...")
    if os.path.isfile("host_map.json"):
        fullpath_host_map = "%s/host_map.json" % os.path.abspath("./host_map.json")  
        cbt_config_gen = cbt_config_scribe.cbt_config_transcriber("ALC", find_cbt_config(), fullpath_host_map)
    else:
        cbt_config_gen = cbt_config_scribe.cbt_config_transcriber("ALC", find_cbt_config())
    
    logger.info("Done")
                    
def find_cbt_config():
    for dirpath, dirs, files in os.walk("."):
            if 'cbt_config.yaml' in files:
                config_fullpath = os.path.join(dirpath,"cbt_config.yaml")
                return config_fullpath
                    
                    
if __name__ == '__main__':
    main()