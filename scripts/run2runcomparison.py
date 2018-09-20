#! /usr/bin/python

import logging
import getopt
import sys
import time
import json
import datetime
import hashlib
from datetime import timedelta
from time import gmtime

from elasticsearch import Elasticsearch, helpers
from util.common_logging import setup_loggers
from proto_py_es_bulk import *



logger = logging.getLogger("index_cbt")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    print "start"
    #TODO instead of only supporting A:B comparisons, try using a comma seperated list in order to provide 1:* comparisons 
    es, comparison_id, test_list = argument_handler()
    
    
#     for i in test_data_generator(es, comparison_id, test_list):
#         print json.dumps(i, indent=1)
    
    
    res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, test_data_generator(es, comparison_id, test_list))
       
    FMT = '%Y-%m-%dT%H:%M:%SGMT'
    start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
    end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
       
    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)
    tdelta = end_t - start_t
    logger.info("Duration of indexing - %s" % tdelta)
    logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 
     

def test_data_generator(es, com_id, test_id_list):
    object_generator = get_test_data(es, com_id, test_id_list)

    for obj in object_generator:
        for action in obj.emit_actions(): 
            yield action
            
def get_test_data(es, comparison_id, test_id_list):
    
    start_time = time.time()
    logger.info("comparison start time - %s" % start_time)
    
    for test_id in test_id_list:
        obj = test_holder(es, test_id, comparison_id, start_time)
        yield obj 
    

class test_holder():
    def __init__(self, es, test_id, comparison_id, start_time):
        self.test_id = test_id
        self.comparison_id = comparison_id
        self.start_datetime_stamp = datetime.datetime.fromtimestamp(start_time) 
        self.offset = ""
        self.offset_map = {}
        self.es = es
        
    def reset_offset(self, initial_time, index):
        
           #S print self.offset_map
            if index in self.offset_map:
                self.offset = self.offset_map[index]
            else:
                new_offset = self.start_datetime_stamp - datetime.datetime.strptime(initial_time, '%Y-%m-%dT%H:%M:%S.%fZ')
                self.offset = new_offset
                self.offset_map[index] = new_offset
                
    def emit_actions(self):
              
        previous_index = ""
        doc_count = 0
        
        indices = self.es.indices.get_alias("*")
        
        index_list=""
        for i in indices:
            if "run2run" not in i:
                if index_list: 
                    index_list = "%s,%s" % (index_list, i)
                else:
                    index_list = "%s" % (i)
        
        results = self.es.search(
            index=index_list,
            size=10000,
            scroll='2m',
            sort="date:increasing",
            body={"query": {"match": {"ceph_benchmark_test.common.test_info.test_id.keyword": self.test_id}}})
        
        sid = results['_scroll_id']
        scroll_size = results['hits']['total']
  
  
        logger.info("Extracting data for %s" % self.test_id)
        logger.info("%d documents found" % results['hits']['total'])
        
        while (scroll_size > 0):
            print "Scrolling..."
            
            page_data = self.es.scroll(scroll_id = sid, scroll = '2m')
            sid = page_data['_scroll_id']
            scroll_size = len(page_data['hits']['hits'])
            doc_count += scroll_size
            print "Document count: " + str(doc_count)
            
            for doc in page_data['hits']['hits']:
                importdoc = {}
                current_index = doc["_index"].strip()
                
                if current_index != previous_index:
                    print "CHANGING OFFSET"
                    #print current_index, previous_index
                    self.reset_offset(doc["_source"]["date"], current_index)
                    previous_index = current_index
                    
                    
                record_time = datetime.datetime.strptime(doc["_source"]["date"], '%Y-%m-%dT%H:%M:%S.%fZ')
                skew_time = record_time + self.offset
                str_skew_time = skew_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    
                importdoc["_source"] = doc["_source"]
                importdoc["_source"]["comparison_ID"] = self.comparison_id
                importdoc["_source"]["date"] = str_skew_time
                
                index_prefix = doc["_index"]
                importdoc["_index"] = "%s-run2run-timeskew-comparison" % index_prefix
                importdoc["_type"] = doc["_type"]
                importdoc["_op_type"] = "create"
                importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                yield importdoc

def argument_handler():
    comparison_id = ""
    test_list = ""
    host = ""
    esport = ""
    log_level = logging.INFO
    usage = """ 
            Usage:
                run2runcomparison.py -t <title> -tl <test1,test2,test3> -h <host> -p <port> 
                
                -t or --title - test identifier
                -tl or --test-list - comma seperated list of all test to be comparted
                -h or --host - Elasticsearch host ip or hostname
                -p or --port - Elasticsearch port (elasticsearch default is 9200)
                -d or --debug - enables debug (verbose) logging output
            """
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 't:l::h:p:d', ['title=', 'test-list=', 'host=', 'port=', 'debug'])
    except getopt.GetoptError:
        print usage 
        exit(1)

    for opt, arg in opts:
        if opt in ('-t', '--title'):
            comparison_id = arg
        if opt in ('-l', '--test-list'):
            test_list = arg.split(',')
        if opt in ('-h', '--host'):
            host = arg
        if opt in ('-p', '--port'):
            esport = arg
        if opt in ('-d', '--debug'):
            log_level = logging.DEBUG
                       
    setup_loggers(log_level)    
    
    if host and comparison_id and esport:
        logger.info("Comparison_id: %s - Comparing %s " % (comparison_id, test_list))
        logger.info("Using Elasticsearch host and port: %s:%s " % (host, esport))
    else:
        print host, comparison_id, esport
        logger.error(usage)
#        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
        exit ()

    es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        )
    
    return es, comparison_id, test_list








if __name__ == '__main__':
    main()
