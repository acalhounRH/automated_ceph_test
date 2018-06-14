#! /usr/bin/python

import os, sys, json, time, types
from time import gmtime, strftime
from elasticsearch import Elasticsearch
from decimal import Decimal

#get args 
if len(sys.argv) > 3:
    test1 = sys.argv[1]
    test2 = sys.argv[2]
    host = sys.argv[3]
    esport = sys.argv[4]
else:
    print "need more args, test 1, test 2, host, port" 

#setup elasticsearch connection
es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
     )


print ("Comparing %s Versus %s ") % (test1, test2)
#initialize vars
test1_doc = {}
test2_doc = {}
operations_array = []
object_size_array = []

#get test 1 results
test1_results = es.search(index="cbt_librbdfio-summary-index", doc_type="fiologfile", size=10000,  body={"query": {"match": {"test_id.keyword": test1}}})
print("Test1  %d documents found" % test1_results['hits']['total'])

#get test 2 results
test2_results = es.search(index="cbt_librbdfio-summary-index", doc_type="fiologfile", size=10000, body={"query": {"match": {"test_id.keyword": test2}}})
print("Test2 %d documents found" % test2_results['hits']['total'])


#process test 1 results
for doc in test1_results['hits']['hits']:
    #print json.dumps(test1_doc, indent=1)
    if doc['_source']['operation'] not in operations_array:
        operations_array.append(str(doc['_source']['operation']))
    if doc['_source']['object_size'] not in object_size_array:
        object_size_array.append(doc['_source']['object_size'])

    if doc['_source']['operation'] not in test1_doc:
        test1_doc[doc['_source']['operation']] = {}
    
    test1_doc[doc['_source']['operation']][doc['_source']['object_size']] = doc['_source']['total-iops']
   # print("Test 1 (%s) %s %s %s" % (doc['_source']['test_id'], doc['_source']['operation'], doc['_source']['total-iops'], doc['_source']['object_size']))

#process test 2 results
for doc in test2_results['hits']['hits']:
    if doc['_source']['operation'] not in operations_array and doc['_source']['object_size']:
        operations_array.append(str(doc['_source']['operation']))
    if doc['_source']['object_size'] not in object_size_array:
        object_size_array.append(doc['_source']['object_size'])
    
    if doc['_source']['operation'] not in test2_doc:
        test2_doc[doc['_source']['operation']] = {}
    test2_doc[doc['_source']['operation']][doc['_source']['object_size']] = doc['_source']['total-iops']
    #print("Test 2 (%s) %s %s %s" % (doc['_source']['test_id'], doc['_source']['operation'], doc['_source']['total-iops'], doc['_source']['object_size'] ))



#print json.dumps(test1_doc, indent=1)
#print json.dumps(test2_doc, indent=1)

object_size_array.sort()

#perform analysis of results
for operation in operations_array:
    for object_size in object_size_array:
        rdelta = round(((test2_doc[operation][object_size] - test1_doc[operation][object_size]) / test1_doc[operation][object_size]) * 100, 3)
        print (operation, object_size, rdelta)
        #print ("((%s - %s) / %s) = %s" % (test1_doc[operation][object_size], test2_doc[operation][object_size], test1_doc[operation][object_size], rdelta ))


