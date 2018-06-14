#! /usr/bin/python

import os, sys, json, time, types
from time import gmtime, strftime
from elasticsearch import Elasticsearch


if len(sys.argv) > 3:
    averdoc['test_id'] = sys.argv[1]
    test1 = sys.argv[3]
    host = sys.argv[3]
    esport = sys.argv[4]
else:
    print "need more args, test 1, test 2, host, port" 

    
es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
     )


res = es.search(index="cbt_librbdfio-summary-index", doc_type="fiologfile", body={"query": {"match": {"test_id": test1}}})


