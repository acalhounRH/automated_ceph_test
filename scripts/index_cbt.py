#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, getopt, multiprocessing
from time import gmtime, strftime, sleep
from elasticsearch import Elasticsearch, helpers
from random import randint

from proto_py_es_bulk import *
from scribes import *
from utils.common_logging import setup_loggers
from analyzers import *


logger = logging.getLogger("index_cbt")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

_max_subprocesses = multiprocessing.cpu_count() / 2

def main():
    arguments = argument_handler()
    
    processed_analyzer_list = process_data(arguments.test_id)
    setup_process_list = True
    try:
        process_count = 0
        run = True
        while run:
            logger.info("STARTING process tasking")
            staging_analyzer_obj_list = []
            if setup_process_list:
                for i in range(_max_subprocesses):
                    try:
                        cur_analyzer_obj = processed_analyzer_list.pop(0)
                        staging_analyzer_obj_list.append(cur_analyzer_obj)
                        logger.debug(len(processed_analyzer_list))
                    except:
                        logger.info("No more iteams")
                        run = False 
                setup_process_list = False
            
            process_list = [] 
            for analyzer_obj in staging_analyzer_obj_list:
                pname = "Process-%s" % process_count 
                process = multiprocessing.Process(name=pname, target=indexer_wrapper, args=(analyzer_obj,arguments))
                process_list.append(process)
                process_count += 1
    
            for process in process_list:
                process.start()
                 
            for process in process_list:
                process.join()
                
            logger.info("Done with current processes")
            setup_process_list = True
        logger.info("ALL DONE")
   
    except Exception as e:
        if "NoneType" in e.message:
            logger.error("No data Found!")
        else:
            logger.exception(e.message)
            


def tester(obj1, obj2):
    logger.info("This is just a test")
    
def indexer_wrapper(analyzer_obj,arguments):
    
    A = randint(5,10)
    B = randint(20,35)
    sleep(randint(A,B))
    if True:
        logger.info("*********** TEST MODE **********")
        for i in process_data_generator(analyzer_obj):
            if arguments.verbose:
                logger.debug(json.dumps(i, indent=4))
        logger.info("*********** TEST MODE **********")
    else:
        try:
            res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(arguments.es, process_data_generator(analyzer_obj))
                
            FMT = '%Y-%m-%dT%H:%M:%SGMT'
            start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
            end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
                
            start_t = datetime.datetime.strptime(start_t, FMT)
            end_t = datetime.datetime.strptime(end_t, FMT)
            tdelta = end_t - start_t
            logger.info("Duration of indexing - %s" % tdelta)
            logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 
        except e as exception:
            logger.error(e.message)
            sys.exit(1)

def process_data_generator(analyzer_obj):
    
    for scribe in analyzer_obj.emit_scribes():
        for action in scribe.emit_actions():
            yield action

def process_data(test_id):
    #test_metadata = {}
    test_metadata = { 
        "ceph_benchmark_test": {
            "application_config": { 
                "ceph_config": {} 
                },
            "common": {
                "hardware": {}, 
                "test_info": {
                    "test_id": test_id 
                    }
                },
            "test_config": {}
            }
        }
                        
    factory =  analyzer_factory.analyzer_factory
    analyzer_obj_list = []
    #parse cbt achive dir and call process method
    for dirpath, dirs, files in os.walk("."):
        for filename in files:
            fname = os.path.join(dirpath,filename)
            #capture cbt configuration 
            if 'cbt_config.yaml' in fname:
                logger.info("Gathering cbt configuration settings...")
                cbt_config_gen = cbt_config_scribe.cbt_config_transcriber(test_id, fname)
#                 benchmark_name = cbt_config_gen.config['benchmarks']
#                 analyzer_obj = factory.factory(benchmark_name, dirpath, cbt_config_gen, test_metadata, "archive")
#                 analyzer_obj_list.append(analyzer_obj)
#                
#                 #if radons bench test, process data 
#                 if "radosbench" in cbt_config_gen.config['benchmarks']:
#                     logger.warn("rados bench is under development")
#                     analyze_cbt_rados_results_generator = cbt_rados_analyzer.analyze_cbt_rados_results(dirpath, cbt_config_gen, copy.deepcopy(test_metadata))
#                     for rados_obj in analyze_cbt_rados_results_generator:
#                         yield rados_obj

            if 'benchmark_config.yaml' in fname:
                benchmark_data = yaml.load(open(fname))
                test_metadata['ceph_benchmark_test']['test_config'] = benchmark_data['cluster']
                
                benchmark_name = test_metadata['ceph_benchmark_test']['test_config']['benchmark']
                
                op_size_bytes = test_metadata['ceph_benchmark_test']['test_config']['op_size']
                time_w_unit = test_metadata['ceph_benchmark_test']['test_config']['time']
                
                if op_size_bytes: 
                     op_size_kb = int(op_size_bytes) / 1024
                     test_metadata['ceph_benchmark_test']['test_config']['op_size'] = op_size_kb
                
                try:
                    if "S" in time_w_unit:  
                        time_wo_unit = time_w_unit.strip("S")
                        time_wo_unit = int(time_wo_unit)
                except:
                    time_wo_unit = time_w_unit
                    test_metadata['ceph_benchmark_test']['test_config']['time'] = time_wo_unit
                    
                args = (dirpath, cbt_config_gen, test_metadata, "benchmark")
                analyzer_obj = factory.factory(benchmark_name, dirpath, cbt_config_gen, test_metadata, "benchmark")
                analyzer_obj_list.append(analyzer_obj)
                
    return analyzer_obj_list

class argument_handler():
    def __init__(self):
        self.test_id = ""
        self.host = ""
        self.port = ""
        self.log_level = logging.INFO
        self.test_mode = False
        self.output_file=None
        self.verbose=False
        
        usage = """ 
                Usage:
                    index_cbt.py -t <test id> -h <host> -p <port>
                    
                    -t or --test_id - test identifier
                    -h or --host - Elasticsearch host ip or hostname
                    -p or --port - Elasticsearch port (elasticsearch default is 9200)
                    -d or --debug - enables debug (verbose) logging output
                """
        try:
            opts, _ = getopt.getopt(sys.argv[1:], 't:h:p:o:dvT', ['output_file', 'test_id=', 'host=', 'port=', 'debug', 'test_mode', 'verbose'])
        except getopt.GetoptError:
            print usage 
            exit(1)
    
        for opt, arg in opts:
            if opt in ('-t', '--test_id'):
                self.test_id = arg
            if opt in ('-h', '--host'):
                self.host = arg
            if opt in ('-p', '--port'):
                self.esport = arg
            if opt in ('-T', '--test_mode'):
                self.test_mode = True
            if opt in ('-o', '--output_file'):
                self.output_file = arg
            if opt in ('-d', '--debug'):
                self.log_level = logging.DEBUG
            if opt in ('-v', '--verbose'):
                self.verbose = True
                           
        setup_loggers("index_cbt", self.log_level)    
        
        if self.host and self.test_id and self.esport:
            logger.info("Test ID: %s, Elasticsearch host and port: %s:%s " % (self.test_id, self.host, self.esport))
        else:
            logger.error(usage)
    #        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
            exit (1)
    
        self.es = Elasticsearch(
            [self.host],
            scheme="http",
            port=self.esport,
            )
 
if __name__ == '__main__':
    main()





