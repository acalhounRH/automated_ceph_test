#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging
import datetime
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
import threading
from threading import Thread
from collections import deque

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(threadName)s: %(levelname)s - %(message)s ')
    maindoc = {}
    threads1 = []
    maindoc["_index"] = "pbench"
    maindoc["_type"] = "pbenchdata"
    maindoc["_source"] = {}

    #check for test id, if not set generic test id
    if len(sys.argv) > 3:
        maindoc["_source"]['test_id'] = sys.argv[1]
        host = sys.argv[2]
        esport = sys.argv[3]
    else: 
        maindoc["_source"]['test_id'] = "librbdfio-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())

    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        ) 
    #if the pbench index doesnt exist create index
    if not es.indices.exists("pbench"):
        request_body = {"settings" : {"refresh_interval": "10s", "number_of_replicas": 0}}
        res = es.indices.create(index="pbench", body=request_body)
        logging.debug("response: '%s' " % (res))
    
    bulk_status = (es.cat.thread_pool(thread_pool_patterns='bulk', format=json))
    print "%s" % bulk_status.split(" ")[3]
    for dirpath, dirs, files in os.walk("."):	
	for filename in files:
        	fname = os.path.join(dirpath,filename)
        	#for each benchmark capture benchmark metadata and process all pbench data
        	if 'benchmark_config.yaml' in fname:
			bdoc = copy.deepcopy(maindoc)
			t1 = Thread(target=t_process_benchmark_data, args=(fname, dirpath, bdoc))
			threads1.append(t1)
    for thread in threads1:
    	thread.start()
    for thread in threads1:
    	try:
        	thread.join()
        except:
        	logger.exception("failed")
	

def t_process_benchmark_data(file_name, test_directory, headerdoc):
	threads2 = []
	benchmarkdoc = copy.deepcopy(headerdoc)
        for line in open(file_name, 'r'):
        	line = line.strip()
                if 'mode:' in line:
                	benchmarkdoc['_source']['mode'] = line.split('mode:', 1)[-1]
                elif 'op_size' in line:
                	benchmarkdoc['_source']['object_size'] = int(line.split('op_size:', 1)[-1]) / 1024
                elif 'benchmark:' in line:
                	benchmarkdoc['_source']['benchmark'] = line.split('benchmark:', 1)[-1]
        #For each host in tools default add to thread array for pushing data to Elasticsearch
	logging.info('processing data in benchmark %s, mode %s, object size %s' % (benchmarkdoc['_source']['benchmark'], benchmarkdoc['_source']['mode'], benchmarkdoc['_source']['object_size']))
        hosts_dir = "%s/tools-default" % test_directory
        for host_dir in os.listdir(hosts_dir):
        	host_dir_fullpath = "%s/%s" % (hosts_dir, host_dir) 
		tmpdoc = copy.deepcopy(benchmarkdoc)
                t = Thread(target=push_bulk_pbench_data_to_es, args=(host_dir_fullpath,tmpdoc))
                threads2.append(t)
        #start all threads 
        for thread in threads2:
                thread.start()
                #wait for all threads to complete
        for thread in threads2:
                try:
                	thread.join()                
                except: 
                        logger.exception("failed")


def push_bulk_pbench_data_to_es(host_dir, headerdoc):
 
    for pdirpath, pdirs, pfiles in os.walk(host_dir.strip()):
        for pfilename in pfiles:
            pfname = os.path.join(pdirpath, pfilename)
            if ".csv" in pfname:

                pbenchdoc = copy.deepcopy(headerdoc)
		#print json.dumps(pbenchdoc, indent=1)
                col_ary = []
                actions = []
                first_row = True

                pbenchdoc['_source']['host'] = pfname.split("/")[5]
                pbenchdoc['_source']['tool'] = pfname.split("/")[6]
                pbenchdoc['_source']['file_name'] = pfname.split("/")[8]
                logging.info('proccesing %s' % pbenchdoc['_source']['file_name'])
		#logging.debug('starting with %s actions' % len(actions))
		starttime_process_file = datetime.datetime.now()
		with open(pfname) as csvfile:
                    readCSV = csv.reader(csvfile, delimiter=',')
                    for row in readCSV:
                        if first_row:
                            #logging.debug("Performing Bulk import of file %s for host %s" % (pbenchdoc['_source']['file_name'], pbenchdoc['_source']['host']))
                            col_num = len(row)
                            for col in range(col_num):
                                col_ary.append(row[col])
                                first_row = False
                        else:
                            for col in range(col_num):
                                if 'timestamp_ms' in col_ary[col]:
                                    ms = float(row[col])
                                    thistime = datetime.datetime.fromtimestamp(ms/1000.0)
                                    pbenchdoc['_source']['date'] = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                else:
                                    if 'pidstat' in pbenchdoc['_source']['tool']:
                                            
                                        pname = col_ary[col].split('/')[-1]
                                        if "ceph-osd" in pname or "ceph-mon" in pname or "ceph-mgr" in pname:
                                            piddoc = copy.deepcopy(pbenchdoc)
                                            pid = col_ary[col].split('-', 1)[0]
                                            piddoc['_source']['process_name'] = pname
                                            piddoc['_source']['process_pid'] = pid
                                            piddoc['_source']['process_value'] = float(row[col])   
                                            a = copy.deepcopy(piddoc)
                                    elif 'sar' in pbenchdoc['_source']['tool'] and "network_" in pbenchdoc['_source']['file_name']:
                                        sardoc = copy.deepcopy(pbenchdoc)
                                        sardoc['_source']['network_interface'] = col_ary[col]
                                        sardoc['_source']['network_value'] = float(row[col])
                                        a = copy.deepcopy(sardoc)
                                    elif 'sar' in pbenchdoc['_source']['tool'] and "memory_" in pbenchdoc['_source']['file_name']:
                                        sardoc = copy.deepcopy(pbenchdoc)
                                        sardoc['_source']['memory_stat'] = col_ary[col]
                                        sardoc['_source']['memory_value'] = float(row[col])
                                        a = copy.deepcopy(sardoc)
                                    elif 'sar' in pbenchdoc['_source']['tool'] and "per_cpu_" in pbenchdoc['_source']['file_name']:
                                        sardoc = copy.deepcopy(pbenchdoc)
                                        sardoc['_source']['sarcpu_stat'] = col_ary[col]
                                        sardoc['_source']['sarcpu_value'] = float(row[col])
                                        a = copy.deepcopy(sardoc)
                                    elif 'iostat' in pbenchdoc['_source']['tool']:
                                        iostatdoc = copy.deepcopy(pbenchdoc)
                                        iostatdoc['_source']['deivce'] = col_ary[col]
                                        iostatdoc['_source']['iops_value'] = float(row[col])
                                        a = copy.deepcopy(iostatdoc)
				    elif 'mpstat' in pbenchdoc['_source']['tool']:
					mpstat = copy.deepcopy(pbenchdoc)
					mpstat['_source']['cpu_stat'] = col_ary[col]
					mpstat['_source']['cpu_value'] = float(row[col])
					
				try:
		                    	actions.append(a)
					index = True
				except:
					index = False 
		stoptime_process_file = datetime.datetime.now()
		if index:  
			process_duration = (stoptime_process_file-starttime_process_file).total_seconds()
			logging.debug("throttling for %s seconds" % process_duration)
			time.sleep(process_duration)
			starttime_bulk_import = datetime.datetime.now()
			try:
				bulk_status = int((es.cat.thread_pool(thread_pool_patterns='bulk', format=json)).split(" ")[3])
				logging.info("********* %s ******" % bulk_status)
				wait_counter=1
				while bulk_status > 85:
					wait_time = 30 * wait_counter
					logging.warn("bulk thread pool high(%s), throttling for %s seconds" % (bulk_status, wait_time))
					time.sleep(wait_time)
					if wait_counter == 4:
						wait_counter = 1 
					else:
						wait_counter += 1
					bulk_status = int((es.cat.thread_pool(thread_pool_patterns='bulk', format=json)).split(" ")[3])
					
					
				logging.info('Starting bulk indexing...')
	                        deque(helpers.parallel_bulk(es, actions, chunk_size=250, thread_count=1, request_timeout=60), maxlen=0)
				stoptime_bulk_import = datetime.datetime.now()
				bulk_duration = (stoptime_bulk_import-starttime_bulk_import).total_seconds()
				logging.debug("throttling for %s seconds" % bulk_duration)
				time.sleep(bulk_duration)
                 	except Exception as e:
				bulk_status = (es.cat.thread_pool(thread_pool_patterns='bulk', format=json)).split(" ")[3]
				stoptime_bulk_import = datetime.datetime.now()
                                bulk_duration = (stoptime_bulk_import-starttime_bulk_import).total_seconds()
                                logging.debug("throttling for %s seconds" % bulk_duration)
	                        logging.error("Failed to update %s bulk thread-pool is %s " % (pbenchdoc['_source']['file_name'], bulk_status)) 
				time.sleep(bulk_duration)
		else:
			logging.debug('not importing %s' % pbenchdoc['_source']['file_name'])
                        

if __name__ == '__main__':
    main()
