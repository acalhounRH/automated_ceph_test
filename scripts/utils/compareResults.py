#! /usr/bin/python

import os, sys, json, time, types, copy, hashlib
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
from decimal import Decimal
from collections import deque
import itertools as it

def main():
    #get args 
    
    print ("test")
    if len(sys.argv) > 2:
        t1 = sys.argv[1]
        t2 = sys.argv[2]
        host = sys.argv[3]
        esport = sys.argv[4]
    else:
        print ("need more args,  host, port") 
        sys.exit()

    #setup elasticsearch connection
    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        )



    #setup elasticsearch main doc
    comparison_results_doc = {}
    comparison_results_doc["_index"] = "cbt-librbdfio-comparison"
    comparison_results_doc["_type"] = "comparisondata"
    
    #find all test results 
#    result = es.search(index="cbt_librbdfio-summary-index", doc_type="fiologfile", size=10000, body={"query": {"match_all": {}}})
#    print("Test list %d documents found" % result['hits']['total'])
    
    # create list of test ids, then create a list of all possible cominations of test results
#    test_array = []
#    for item in  result['hits']['hits']:
#        if item['_source']['test_id'] not in test_array:
#                test_array.append(item['_source']['test_id'])

#    test_combo = list(it.combinations(test_array, 2))
    #test_combo = list(it.permutations(test_array, 2))

    #evaluate the percent difference between all combinations of test results
#    for test in test_combo:
#        compare_result(test[0], test[1], comparison_results_doc)
    compare_result(t1, t2, comparison_results_doc)


def compare_result(test1, test2, headerdoc):

    result_doc = copy.deepcopy(headerdoc)
    result_doc["_source"] = {}
    result_doc["_source"]['test1'] = test1
    result_doc["_source"]['test2'] = test2
    result_doc["_op_type"] = "create"

    print ("Comparing %s Versus %s " % (test1, test2))

    test1_doc = {}
    test2_doc = {}
    operations_array = []
    object_size_array = []


    #get test 1 results
    index_list="cbt_librbdfio-summary-indextest1-fixed,cbt_radosbench-summary-index"
    test1_results = es.search(index=index_list, size=10000,  body={"query": {"match": {"ceph_benchmark_test.common.test_info.test_id.keyword": test1}}})
    print("Test1  %d documents found" % test1_results['hits']['total'])

    #get test 2 results
    test2_results = es.search(index=index_list, size=10000, body={"query": {"match": {"ceph_benchmark_test.common.test_info.test_id.keyword": test2}}})
    print("Test2 %d documents found" % test2_results['hits']['total'])


    #process test 1 results
    ft = True
    for doc in test1_results['hits']['hits']:
        
        if "total-iops" in doc['_source']["ceph_benchmark_test"]["test_data"]:
            operation = doc['_source']["ceph_benchmark_test"]["test_data"]['operation']
            object_size = doc['_source']["ceph_benchmark_test"]["test_data"]['object_size']
            total_iops = float(doc['_source']["ceph_benchmark_test"]["test_data"]['total-iops'])
            if ft:
                result_doc["_source"]['date'] = doc["_source"]['date']
                ft = True
            #print json.dumps(test1_doc, indent=1)
            if operation not in operations_array:
                operations_array.append(str(operation))
            if object_size not in object_size_array:
                object_size_array.append(object_size)
    
            if operation not in test1_doc:
                test1_doc[operation] = {}
        
            test1_doc[operation][object_size] = total_iops

    #process test 2 results
    for doc in test2_results['hits']['hits']:
        
        if "total-iops" in doc['_source']["ceph_benchmark_test"]["test_data"]:
            operation = doc['_source']["ceph_benchmark_test"]["test_data"]['operation']
            object_size = doc['_source']["ceph_benchmark_test"]["test_data"]['object_size']
            total_iops = float(doc['_source']["ceph_benchmark_test"]["test_data"]['total-iops'])
            
            if operation not in operations_array:
                operations_array.append(str(operation))
            if object_size not in object_size_array:
                object_size_array.append(object_size)
            
            if operation not in test2_doc:
                test2_doc[operation] = {}
            test2_doc[operation][object_size] = total_iops
    
    object_size_array.sort()

    #perform analysis of results
    actions = []
    average_delta_list = []
    for operation in operations_array:
        for object_size in object_size_array: 
            rdelta = round(((test2_doc[operation][object_size] - test1_doc[operation][object_size]) / test1_doc[operation][object_size]) * 100, 3)
            #print "%s = (%s - %s / %s) * 100" % (rdelta, test2_doc[operation][object_size], test1_doc[operation][object_size], test1_doc[operation][object_size])
            average_delta_list.append(rdelta) 
            c_results = copy.deepcopy(result_doc)
            c_results['_source']['operation'] = operation
            c_results['_source']['%sKB' % object_size] = rdelta

            c_results["_id"] = hashlib.md5(str(c_results).encode()).hexdigest()
            a = copy.deepcopy(c_results)
            actions.append(a)
            
    c_results = copy.deepcopy(result_doc)
    average_delta = round((sum(average_delta_list)/len(average_delta_list)), 3)
    c_results['_source']['average_delta'] = average_delta
    c_results["_id"] = hashlib.md5(str(c_results).encode()).hexdigest()
    a = copy.deepcopy(c_results)
    actions.append(a)

    deque(helpers.parallel_bulk(es, actions, chunk_size=250, thread_count=1, request_timeout=60), maxlen=0)


if __name__ == '__main__':
    main()

