#! /usr/bin/python

import os, sys, json, time, types, csv, copy
from time import gmtime, strftime
import datetime
import logging
from elasticsearch import Elasticsearch, helpers
from collections import deque

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(threadName)s %(message)s ')
#time (msec), value, data direction, block size (bytes), offset (bytes)

#Time for the log entry is always in milliseconds. The value logged depends on the type of log, it will be one of the
#following:
#Latency log Value is latency in nsecs
#Bandwidth log Value is in KiB/sec
#IOPS log Value is IOPS
#Data direction is one of the following:
#0 I/O is a READ
#1 I/O is a WRITE
#2 I/O is a TRIM

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

path = os.getcwd()
newdoc = {}
newdoc["_index"] = "cbt_librbdfio-log-index"
newdoc["_type"] = "librbdfiologdata"
newdoc["_source"] = {}
iteration_ary = []
actions = []


if len(sys.argv) > 3:
    newdoc["_source"]['test_id'] = sys.argv[1]
    host = sys.argv[2]
    esport = sys.argv[3]
else:
    newdoc["_source"]['test_id'] = "librbdfio-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())
    

es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
     )

if not es.indices.exists("cbt_librbdfio-log-index"):

    request_body = {
        "settings" : {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    res = es.indices.create(index="cbt_librbdfio-log-index", body=request_body)
    print ("response: '%s' " % (res))


dirs = sorted(listdir_fullpath(path), key=os.path.getctime) #get iterations dir in time order
for cdir in dirs:
    if os.path.isdir(cdir):
        if os.path.basename(cdir) not in iteration_ary: iteration_ary.append(os.path.basename(cdir))
        test_dirs = sorted(listdir_fullpath(cdir), key=os.path.getctime) # get test dir in time order
        newdoc["_source"]['iteration'] = os.path.basename(cdir)

        for test_dir in test_dirs:
            with open('%s/benchmark_config.yaml' % test_dir) as myfile: # open benchmarch_config.yaml and check if test is librbdfio 
                if 'benchmark: librbdfio' in myfile.read():
                    for line in open('%s/benchmark_config.yaml' % test_dir,'r').readlines():
                        line = line.strip()
                        if 'mode:' in line:
                            newdoc["_source"]['mode'] = line.split('mode:', 1)[-1]
                        if 'op_size:' in line:
                            newdoc["_source"]['object_size'] = int(line.split('op_size:', 1)[-1]) / 1024
                    test_files = sorted(listdir_fullpath(test_dir), key=os.path.getctime) # get all samples from current test dir in time order
                    for file in test_files:
                        if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):
                            logging.info('importing %s into elasticsearch' % file)
                            jsonfile = "%s/json_%s.%s" % (test_dir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
                            newdoc["_source"]['host'] = os.path.basename(file).split('log.', 1)[1] 
                            jsondoc = json.load(open(jsonfile))
                            test_time_ms = long(jsondoc['timestamp_ms'])
                            test_duration_ms = long(jsondoc['global options']['runtime']) * 1000
                            start_time = test_time_ms - test_duration_ms

                            newdoc["_source"]['file'] = os.path.basename(file)
                            with open(file) as csvfile:
                                readCSV = csv.reader(csvfile, delimiter=',')
                                for row in (readCSV):
                                    ms = float(row[0]) + float(start_time)
                                    newtime = datetime.datetime.fromtimestamp(ms/1000.0)
                                    newdoc["_source"]['date'] = newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                    newdoc["_source"]['value'] = int(row[1])
                                    newdoc["_source"]['data direction'] = row[2]
                                    #print json.dumps(newdoc, indent=1)
                                    a = copy.deepcopy(newdoc)
                                    actions.append(a)
                                    #res = es.index(index="cbt_librbdfio-log-index", doc_type='fiologfile', body=newdoc)
                                    #print(res['result'])
#                                    del newdoc["_source"]['date']
#                                    del newdoc["_source"]['value']
#                                    del newdoc["_source"]['data direction']
                            try:
                                deque(helpers.parallel_bulk(es, actions, chunk_size=500, thread_count=5, request_timeout=60), maxlen=0)
                            except Exception as e:
                                logging.exception("message")

                    
                    #ADD bulk import here 
