#! /usr/bin/python

import os, sys, json, time, types, csv, copy
from time import gmtime, strftime
import datetime
import logging
from elasticsearch import Elasticsearch, helpers
from collections import deque
import threading
from threading import Thread

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(threadName)s %(message)s ')

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def push_bulk_test_logs(tdir, headerdoc):
	total_file = 0
	cur_count = 1
	test_files = sorted(listdir_fullpath(tdir), key=os.path.getctime) # get all samples from current test dir in time order
		
	for file in test_files: #get total number of files
                if ("_iops" in file) or ("_lat" in file):
			total_file += 1
		
        for file in test_files:
        	if ("_iops" in file) or ("_lat" in file):
        	#if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):
			fiologdoc = copy.deepcopy(headerdoc)
                	logging.info('processing %s of %s: file - %s, Test %s' % (cur_count, total_file, os.path.basename(file) ,file.split('/')[7]))
			cur_count += 1
                        jsonfile = "%s/json_%s.%s" % (tdir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
                        fiologdoc["_source"]['host'] = os.path.basename(file).split('log.', 1)[1]
                        jsondoc = json.load(open(jsonfile))
                        test_time_ms = long(jsondoc['timestamp_ms'])
                        test_duration_ms = long(jsondoc['global options']['runtime']) * 1000
                        start_time = test_time_ms - test_duration_ms

                        fiologdoc["_source"]['file'] = os.path.basename(file)
			actions = []
                        with open(file) as csvfile:
                        	readCSV = csv.reader(csvfile, delimiter=',')
                                for row in (readCSV):
                                	ms = float(row[0]) + float(start_time)
                                	newtime = datetime.datetime.fromtimestamp(ms/1000.0)
                                	fiologdoc["_source"]['date'] = newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                	fiologdoc["_source"]['value'] = int(row[1])
                                	fiologdoc["_source"]['data direction'] = row[2]
                                	#print json.dumps(fiologdoc, indent=1)
                                	a = copy.deepcopy(fiologdoc)
                                	actions.append(a)
                        	try:
					starttime_bulk_import = datetime.datetime.now()
                                	deque(helpers.parallel_bulk(es, actions, chunk_size=500, thread_count=8, request_timeout=60), maxlen=0)
		                        stoptime_bulk_import = datetime.datetime.now()
					logging.info('starting bulk import...')
		                        bulk_duration = (stoptime_bulk_import-starttime_bulk_import).total_seconds()
		                        logging.debug("finished bluk import, throttling for %s seconds" % bulk_duration)
		                        time.sleep(bulk_duration)
                         	except Exception as e:
                                	logging.exception("message")


path = os.getcwd()
maindoc = {}
maindoc["_index"] = "cbt_librbdfio-log-index"
maindoc["_type"] = "librbdfiologdata"
maindoc["_source"] = {}
iteration_ary = []
threads = []

if len(sys.argv) > 3:
    maindoc["_source"]['test_id'] = sys.argv[1]
    host = sys.argv[2]
    esport = sys.argv[3]
else:
    maindoc["_source"]['test_id'] = "librbdfio-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())

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
        maindoc["_source"]['iteration'] = os.path.basename(cdir)

        for test_dir in test_dirs:
            with open('%s/benchmark_config.yaml' % test_dir) as myfile: # open benchmarch_config.yaml and check if test is librbdfio 
                if 'benchmark: librbdfio' in myfile.read():
                    for line in open('%s/benchmark_config.yaml' % test_dir,'r').readlines():
                        line = line.strip()
                        if 'mode:' in line:
                            maindoc["_source"]['mode'] = line.split('mode:', 1)[-1]
                        if 'op_size:' in line:
                            maindoc["_source"]['object_size'] = int(line.split('op_size:', 1)[-1]) / 1024
		    print test_dir
		    tmpdoc = copy.deepcopy(maindoc)
		    t = Thread(target=push_bulk_test_logs, args=(test_dir,tmpdoc))
		    threads.append(t)
        #start all threads 
        for thread in threads:
        	thread.start()
        #wait for all threads to complete
        for thread in threads:
        	try:
                	thread.join()
                except:
                	logger.exception("failed")

