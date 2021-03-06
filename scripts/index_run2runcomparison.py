#! /usr/bin/python

import logging
import getopt
import sys
import time
import json
import datetime
import hashlib
import string
from datetime import timedelta
from time import gmtime

from elasticsearch import Elasticsearch, helpers
from utils.common_logging import setup_loggers
from proto_py_es_bulk import *

import multiprocessing as mp


logger = logging.getLogger("index_run2runcomparison")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main(): 
    arguments = argument_handler()
    
    output = mp.Queue()
    start_time = datetime.datetime.utcnow()
    logger.info("comparison start time - %s" % start_time)
    series_list = list(string.ascii_uppercase)
    
    series_count=0
    
    process_list = []
    for test in arguments.test_list:
        process = mp.Process(target=index_wrapper, args=(arguments.es, arguments.comparison_id, test, start_time, arguments.test_mode, arguments.verbose, series_list[series_count]))
        process_list.append(process)
        series_count += 1
    
    # Run processes

    for p in process_list:
        p.start()

    for p in process_list:
        p.join()
    
def index_wrapper(es, comparison_id, test_id, start_time, test_mode, verbose, series):
    
    if test_mode:
        logger.info("********************************")
        logger.info("*********** TEST MODE **********")
        logger.info("********************************")
        for i in test_data_generator(es, comparison_id, test_id, start_time, series):
            if "cbt_config" in i:
                logger.debug(json.dumps(i, indent=4))
        logger.info("********************************")
        logger.info("*********** TEST MODE **********")
        logger.info("********************************")
    else:
        res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, test_data_generator(es, comparison_id, test_id, start_time, series))
           
        FMT = '%Y-%m-%dT%H:%M:%SGMT'
        start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
        end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
           
        start_t = datetime.datetime.strptime(start_t, FMT)
        end_t = datetime.datetime.strptime(end_t, FMT)
        tdelta = end_t - start_t
        logger.info("Duration of indexing - %s" % tdelta)
        logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 

def test_data_generator(es, comparison_id, test_id, start_time, series):

    obj = test_holder(es, test_id, comparison_id, start_time, series)
    for action in obj.emit_actions(): 
        yield action 

class test_holder():
    def __init__(self, es, test_id, comparison_id, start_time, series_id):
        self.test_id = test_id
        self.comparison_id = comparison_id
        self.start_datetime_stamp = start_time 
        self.series_id = series_id
        self.offset = ""
        self.offset_map = {}
        self.es = es
        self.TIME_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'
        
    def reset_offset(self, record_time, index):
        
        if index in self.offset_map:
            self.offset = self.offset_map[index]
        else:
            record_time_struc = datetime.datetime.strptime(record_time, self.TIME_FMT)
            new_offset = self.start_datetime_stamp - record_time_struc 
            new_offset_in_sec = new_offset.total_seconds()
            self.offset = new_offset_in_sec
            self.offset_map[index] = new_offset_in_sec
        
        return self.offset
    
    def emit_actions(self):
              
        previous_index = ""
        doc_count = 0
        
        indices = self.es.indices.get_alias("*")
        
        index_list=""
        for i in indices:
            if "run2run" not in i and "metricbeat" not in i and ".monitoring-" not in i and ".kibana" not in i:
                logger.debug("adding %s to index list" % i)
                if index_list:
                    index_list = "%s,%s" % (index_list, i)
                else:
                    index_list = "%s" % (i)
        
        results = self.es.search(
            index=index_list,
            size=10000,
            scroll='2m',
            sort="date:asc",
            body={"query": {"match": {"ceph_benchmark_test.common.test_info.test_id.keyword": self.test_id}}})
        
        sid = results['_scroll_id']
        scroll_size = results['hits']['total']
        remaining_documents = scroll_size
         
        logger.info("Extracting data for %s" % self.test_id)
        logger.info("%d documents found" % results['hits']['total'])
        logger.info("Scrolling search results...")
        page_data=results
        while (scroll_size > 0):
            
            sid = page_data['_scroll_id']
            logger.debug("Remaining Documents: " + str(remaining_documents))
            
            for doc in page_data['hits']['hits']:
                importdoc = {}
                current_index = doc["_index"].strip()
                
                if current_index != previous_index:
                    new_offset = self.reset_offset(doc["_source"]["date"], current_index)
                    previous_index = current_index
                    
                record_time = datetime.datetime.strptime(doc["_source"]["date"], self.TIME_FMT)
                
                skew_time = record_time + timedelta(seconds=new_offset)
                str_skew_time = skew_time.strftime(self.TIME_FMT)
                    
                importdoc["_source"] = doc["_source"]
                
                importdoc["_source"]["comparison_ID"] = self.comparison_id
                importdoc["_source"]['series_id'] = self.series_id
                importdoc["_id"] = hashlib.md5(str(importdoc).encode()).hexdigest()
                importdoc["_source"]["date"] = str_skew_time
                
                
                index_prefix = doc["_index"]
                importdoc["_index"] = "%s-run2run-timeskew-comparison" % index_prefix
                importdoc["_type"] = doc["_type"]
                importdoc["_op_type"] = "create"
                yield importdoc
                
            page_data = self.es.scroll(scroll_id = sid, scroll = '2m')
            scroll_size = len(page_data['hits']['hits'])
            doc_count += scroll_size
            remaining_documents -= scroll_size

class argument_handler():
    def __init__(self):
        self.comparison_id = ""
        self.test_list = ""
        self.host = ""
        self.esport = ""
        self.log_level = logging.INFO
        self.test_mode = False
        self.output_file=None
        self.verbose=False
        
        self.usage = """ 
                Usage:
                    run2runcomparison.py -t <title> -tl <test1,test2,test3> -h <host> -p <port> 
                    
                    -t or --title - test identifier
                    -l or --test-list - comma seperated list of all test to be comparted
                    -h or --host - Elasticsearch host ip or hostname
                    -p or --port - Elasticsearch port (elasticsearch default is 9200)
                    -d or --debug - enables debug (verbose) logging output
                """
                
        try:
            opts, _ = getopt.getopt(sys.argv[1:], 't:l:h:p:o:dTv', ['title=', 'test-list=', 'host=', 'port=', 'debug', "output_file", "test_mode", "verbose"])
        except getopt.GetoptError:
            print (self.usage) 
            exit(1)
    
        for opt, arg in opts:
            if opt in ('-t', '--title'):
                self.comparison_id = arg
            if opt in ('-l', '--test-list'):
                self.test_list = arg.split(',')
            if opt in ('-h', '--host'):
                self.host = arg
            if opt in ('-p', '--port'):
                self.esport = arg
            if opt in ('-d', '--debug'):
                self.log_level = logging.DEBUG
            if opt in ('-T', '--test_mode'):
                self.test_mode = True
            if opt in ('-o', '--output_file'):
                self.output_file = arg
            if opt in ('-v', '--verbose'):
                self.verbose = True
                           
        setup_loggers("index_run2runcomparison", self.log_level)    
        
        if self.host and self.comparison_id and self.esport:
            logger.info("Comparison_id: %s - Comparing %s " % (self.comparison_id, self.test_list))
            logger.info("Using Elasticsearch host and port: %s:%s " % (self.host, self.esport))
        else:
            print (self.host, self.comparison_id, self.esport)
            logger.error(self.usage)
            exit ()
    
        self.es = Elasticsearch(
            [self.host],
            scheme="http",
            port=self.esport,
            )
        

if __name__ == '__main__':
    main()
