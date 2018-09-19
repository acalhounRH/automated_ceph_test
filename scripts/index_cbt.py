#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, getopt
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
from proto_py_es_bulk import *
from scribes import *
from util.common_logging import setup_loggers
from unify_tool_data import  *
from analyzers import *

logger = logging.getLogger("index_cbt")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    es, test_id = argument_handler()
    
    ###: TODO need to add test mode and turn this on and the real streaming bulk call off. 
#     for i in process_data_generator(test_id):
#         print json.dumps(i, indent=1)
  
    res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, process_data_generator(test_id))
      
    FMT = '%Y-%m-%dT%H:%M:%SGMT'
    start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
    end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
      
    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)
    tdelta = end_t - start_t
    logger.info("Duration of indexing - %s" % tdelta)
    logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 


#########################################################################

def argument_handler():
    test_id = ""
    host = ""
    port = ""
    log_level = logging.INFO
    usage = """ 
            Usage:
                evaluatecosbench_pushes.py -t <test id> -h <host> -p <port>
                
                -t or --test_id - test identifier
                -h or --host - Elasticsearch host ip or hostname
                -p or --port - Elasticsearch port (elasticsearch default is 9200)
                -d or --debug - enables debug (verbose) logging output
            """
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 't:h:p:d', ['test_id=', 'host=', 'port=', 'debug'])
    except getopt.GetoptError:
        print usage 
        exit(1)

    for opt, arg in opts:
        if opt in ('-t', '--test_id'):
            test_id = arg
        if opt in ('-h', '--host'):
            host = arg
        if opt in ('-p', '--port'):
            esport = arg
        if opt in ('-d', '--debug'):
            log_level = logging.DEBUG
                       
    setup_loggers(log_level)    
    
    if host and test_id and esport:
        logger.info("Test ID: %s, Elasticsearch host and port: %s:%s " % (test_id, host, esport))
    else:
        logger.error(usage)
#        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
        exit ()

    es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        )
    
    return es, test_id

def process_data_generator(test_id):
    
    object_generator = process_data(test_id)

    for obj in object_generator:
        for action in obj.emit_actions():
            #generate index name and id 
            #I.E add elasticsearch specific information to emitted data. 
            yield action

def process_data(test_id):
    test_metadata = {}
    test_metadata['ceph_benchmark_test'] = {
        "application_config": {
            "ceph_config": {}
            },
        "common": {
            "hardware": {},
            "test_info": {}
            },
        "test_config": {}
        }
    test_metadata['ceph_benchmark_test']['common']['test_info']['test_id'] = test_id
    
    #parse cbt achive dir and call process method
    for dirpath, dirs, files in os.walk("."):
        for filename in files:
            fname = os.path.join(dirpath,filename)
            #capture cbt configuration 
            if 'cbt_config.yaml' in fname:
                logger.info("Gathering cbt configuration settings...")
                cbt_config_gen = cbt_config_scribe.cbt_config_transcriber(test_id, fname)             
                yield cbt_config_gen
            
                #if rbd test, process json data 
                if "librbdfio" in cbt_config_gen.config['benchmarks']:
                    analyze_cbt_fio_results_generator = cbt_fio_analyzer.analyze_cbt_fio_results(dirpath, cbt_config_gen, copy.deepcopy(test_metadata))
                    for fiojson_obj in analyze_cbt_fio_results_generator:
                        yield fiojson_obj
               
                #if radons bench test, process data 
                if "radosbench" in cbt_config_gen.config['benchmarks']:
                    logger.warn("rados bench is under development")
                    analyze_cbt_rados_results_generator = cbt_rados_analyzer.analyze_cbt_rados_results(dirpath, cbt_config_gen, copy.deepcopy(test_metadata))
                    for rados_obj in analyze_cbt_rados_results_generator:
                        yield rados_obj
  
 
if __name__ == '__main__':
    main()





