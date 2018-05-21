#! /usr/bin/python

import os, sys, json, time, types, csv
from time import gmtime, strftime
import datetime
from elasticsearch import Elasticsearch
es = Elasticsearch(
        ['10.18.81.12'],
        scheme="http",
        port=9200,
     )


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

#create index 

if not es.indices.exists("cbt_librbdfio-log-index"):

    request_body = {
        "settings" : {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    res = es.indices.create(index="cbt_librbdfio-log-index", body=request_body)
    print ("response: '%s' " % (res))


def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

path = os.getcwd()
newdoc = {}
iteration_ary = []


if len(sys.argv) > 1:
    newdoc['test_id'] = sys.argv[1]
else: 
    newdoc['test_id'] = "librbdfio-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())
    


dirs = sorted(listdir_fullpath(path), key=os.path.getctime) #get iterations dir in time order
for cdir in dirs:
    if os.path.isdir(cdir):
        if os.path.basename(cdir) not in iteration_ary: iteration_ary.append(os.path.basename(cdir))
        test_dirs = sorted(listdir_fullpath(cdir), key=os.path.getctime) # get test dir in time order
        newdoc['iteration'] = os.path.basename(cdir)

        for test_dir in test_dirs:
            with open('%s/benchmark_config.yaml' % test_dir) as myfile: # open benchmarch_config.yaml and check if test is librbdfio 
                if 'benchmark: librbdfio' in myfile.read():
                    for line in open('%s/benchmark_config.yaml' % test_dir,'r').readlines():
                        line = line.strip()
                        if 'mode:' in line:
                            newdoc['mode'] = line.split('mode:', 1)[-1]
                        if 'op_size:' in line:
                            newdoc['object_size'] = int(line.split('op_size:', 1)[-1]) / 1024
                    test_files = sorted(listdir_fullpath(test_dir), key=os.path.getctime) # get all samples from current test dir in time order
                    for file in test_files:
                        if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):

                            jsonfile = "%s/json_%s.%s" % (test_dir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
                            newdoc['host'] = os.path.basename(file).split('log.', 1)[1] 
                            jsondoc = json.load(open(jsonfile))
                            start_time = jsondoc['timestamp_ms']
                            newdoc['file'] = os.path.basename(file)
                            with open(file) as csvfile:
                                readCSV = csv.reader(csvfile, delimiter=',')
                               # for row in reversed(list(csv.reader(csvfile, delimiter=','))):
                                for row in (readCSV):
                                    #ms = float(start_time) - float(row[0])
                                    ms = float(row[0]) + float(start_time)
                                    newtime = datetime.datetime.fromtimestamp(ms/1000.0)
                                    newdoc['date'] = newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                    newdoc['value'] = int(row[1])
                                    newdoc['data direction'] = row[2]
                                    #print json.dumps(newdoc, indent=1)
                                    res = es.index(index="cbt_librbdfio-log-index", doc_type='fiologfile', body=newdoc)
                                    #print(res['result'])
                                    del newdoc['date']
                                    del newdoc['value']
                                    del newdoc['data direction']
                                csvfile.close() 
