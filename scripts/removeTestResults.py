#! /usr/bin/python

import os, sys, json, time, types, copy
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
from decimal import Decimal
from collections import deque
import itertools as it

def main():
    #get args 
    if len(sys.argv) > 3:
        t1 = sys.argv[1]
        host = sys.argv[2]
        esport = sys.argv[3]
    else:
        print "need more args, test, host, port" 

    #setup elasticsearch connection
    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        )
    
    compare_result(t1)

def compare_result(test1):

    print ("deleting %s") % (test1)
    #get test 1 results
    test1_results = es.delete_by_query(index="pbench", body={"query": {"match": {"test_id.keyword": test1}}}, request_timeout=120)
    print json.dumps(test1_results, indent=1)
#    print("Test1  %d documents found" % test1_results['hits']['total'])

if __name__ == '__main__':
    main()

