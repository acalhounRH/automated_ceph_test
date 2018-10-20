#! /usr/bin/python

import os, sys, json, time, types, copy
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
from decimal import Decimal
from collections import deque
import itertools as it

from elasticsearch import Elasticsearch, helpers
from utils.common_logging import setup_loggers
from proto_py_es_bulk import *


def main():
    #get args 
    if len(sys.argv) > 2:
        t1 = sys.argv[1]
        t2 = sys.argv[2]
        host = sys.argv[3]
        esport = sys.argv[4]
    else:
        print "need more args,  host, port" 

    #setup elasticsearch connection
    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        )

    res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, test_data_generator(es, comparison_id, test_list))
       
    FMT = '%Y-%m-%dT%H:%M:%SGMT'
    start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
    end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
       
    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)
    tdelta = end_t - start_t
    logger.info("Duration of indexing - %s" % tdelta)
    logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 
     
def compare_result_generator():
    
    #find all test results 
    result = es.search(index="cbt_librbdfio-summary-index", doc_type="fiologfile", size=10000, body={"query": {"match_all": {}}})
    print("Test list %d documents found" % result['hits']['total'])
    
    # create list of test ids, then create a list of all possible cominations of test results
    test_array = []
    for item in  result['hits']['hits']:
        if item['_source']['ceph_benchmark_test']['test_info']['test_id'] not in test_array:
                test__id_list.append(item['_source']['ceph_benchmark_test']['test_info']['test_id'])
  
    #test_combo = list(it.combinations(test_array, 2))
    test_combo = list(it.permutations(test_id_list, 2))        
    yield compare_result(test_permutations)


def compare_result(test1, test2, headerdoc):

    result_doc = copy.deepcopy(headerdoc)


    operations_array = []
    object_size_array = []
    test_results_list = []
    for test_combo in test_permutations_list:
        test_counter = 0
        test_doc_list = []
        for test in test_combo:
            test_doc = {}
            new_test_holder = test_holder(test)
    
            ft = True
            for doc in new_test_holder.test_results:
                operation = doc['_source']['ceph_benchmark_test']['test_data']['operation']
                object_size_doc['_source']['ceph_benchmark_test']['test_data']['object_size']
                
                if ft:
                    result_doc["_source"]['date'] = doc["_source"]['date']
                    ft = True
                if operation not in operations_array:
                    operations_array.append(str(operation))
                if object_size not in object_size_array:
                    object_size_array.append(object_size)
        
                if operation not in test_doc:
                    test_doc[operation] = {}
            
                test_doc[operation][object_size] = doc['_source']['ceph_benchmark_test']['test_data']['total-iops']
                test_doc_list[test_counter] = test_doc
        object_size_array.sort()

    #perform analysis of results
    
    result_doc["_source"] = {}
    result_doc["_source"]['test1'] = test1
    result_doc["_source"]['test2'] = test2
    
        actions = []
        for operation in operations_array:
            for object_size in object_size_array:
                rdelta = round(((test_doc_list[1][operation][object_size] - test1_doc[0][operation][object_size]) / test1_doc[0][operation][object_size]) * 100, 3)
                c_results = copy.deepcopy(result_doc)
                c_results['_source']['operation'] = operation
                c_results['_source']['%sKB' % object_size] = rdelta

         #   if rdelta > -5:
         #       print ("PASS: %s %s %s" % (operation, object_size, rdelta))
         #   elif rdelta < -5 and rdelta > -10:
         #       print ("WARN: %s %s %s" % (operation, object_size, rdelta))
         #   elif rdelta < -10:
         #       print ("FAILED: %s %s %s" % (operation, object_size, rdelta))

        #print json.dumps(c_results, indent=1)
            a = copy.deepcopy(c_results)
            actions.append(a)

  #  deque(helpers.parallel_bulk(es, actions, chunk_size=250, thread_count=1, request_timeout=60), maxlen=0)


class test_holder():
    def __init__(self):
        self.test_id = test_id
        self.query_results = es.search(index="cbt_librbdfio-summary-index", 
                                      doc_type="fiologfile", 
                                      size=10000,  
                                      body={ "query": 
                                            { "match": 
                                             { "test_id.keyword": self.test_id}
                                             }
                                            }
                                      )
        self.test_results = self.query_results['hits']['hits']
    

if __name__ == '__main__':
    main()

