#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging
import datetime
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
import threading
from threading import Thread
from collections import deque
import multiprocessing
import getopt

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(process)d %(threadName)s: %(levelname)s - %(message)s ')
    maindoc = {}
    process2 = []
    maindoc["_index"] = "cosbench"
    maindoc["_type"] = "cosbenchdata"
    maindoc["_source"] = {}
    
    test_id = ""
    host = ""
    port = ""
    workload_list = []

    try:
        opts, _ = getopt.getopt(sys.argv[1:], 't:h:p:w:', ['test_id=', 'host=', 'port=', 'workloads'])
    except getopt.GetoptError:
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-t', '--test_id'):
            test_id = arg
            maindoc["_source"]['test_id'] = arg
        if opt in ('-h', '--host'):
            host = arg
        if opt in ('-p', '--port'):
            esport = arg
        if opt in ('-w', '--workloads'):
            tmp_list = arg.split(',')
            for i in tmp_list:
                if "-" in i:
                    a, b = i.split("-")
                    for x in xrange(int(a), int(b)+1):
                        workload_list.append(x)
                else:
                    workload_list.append(int(i))
                    

    if host and test_id and esport and  workload_list:
        logging.info("Test ID: %s, Host: %s, Port: %s " % (test_id, host, esport))
    else:
        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
        exit ()

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
    
    
    run_history = {}
    run_actions = []
    first_row = True
    #process run-history file
    if os.path.isfile("run-history.csv"):
        run_history = copy.deepcopy(maindoc)
        with open("run-history.csv") as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            header_list = []
            counter = 0
            for row in readCSV:
                if first_row:
                    number_of_columns = len(row)
                    first_row = False
                    for column in range(number_of_columns):
                        header_list.append(row[column])
                else:
                    for column in range(number_of_columns):
                        if "Submitted-At" in header_list[column]:
                            run_history['_source'][header_list[column]] = row[column]
                            thistime = datetime.datetime.strptime(row[column], '%Y-%m-%d %H:%M:%S' )
                            run_history['_source']['date'] = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        else:
        
                            if "Id" in header_list[column]:
                                wID = row[column]
                                wID = wID.strip('w')
                                run_history['_source']['Workload ID'] = int(wID)
                            elif "State" in header_list[column] and not "Detailed State" in header_list[column]:
                                if "finished" in row[column]: 
                                    run_history['_source']['StateID'] = 0
                                elif "failed" in row[column]:
                                    run_history['_source']['StateID'] = 3
                                elif "cancelled" in row[column]:
                                    run_history['_source']['StateID'] = 2
                                elif "terminated" in row[column]:
                                    run_history['_source']['StateID'] = 1
                                else:
                                    run_history['_source']['StateID'] = 4

                                run_history['_source'][header_list[column]] = row[column]
                            else:
                                run_history['_source'][header_list[column]] = row[column]
                    
                            a = copy.deepcopy(run_history)
                    if a and run_history['_source']['Workload ID'] in workload_list:
                        run_actions.append(a)
    else:
        logging.error("Unable to find run-history")
        exit()

#    for i in run_actions:
#        print json.dumps(i, indent=1)

#   bluk_import(run_actions)
    
    #Process selected workload stage reports
    stage_actions = []
    stage_doc = copy.deepcopy(maindoc)
    ws_doc = {}
    for dirpath, dirs, files in os.walk("."):
        for wdir in dirs:
            if wdir.startswith("w"):
                wdirID = wdir.split("-")[0]
                wdirID = wdirID.strip('w')
                if int(wdirID) in workload_list:
                    stage_doc = copy.deepcopy(maindoc)
                    ws_doc[wdir] = []
                    stage_doc['_source']['Workload ID'] = int(wdirID)
                    logging.info("Processing %s" % (wdir))
                    with open("%s/%s.csv" % (wdir, wdir)) as csvfile:
                        readCSV = csv.reader(csvfile, delimiter=',')
                        header_list = []
                        first_row = True
                        b = ""
                        for row in readCSV:
                            if first_row:
                                number_of_columns = len(row)
                                first_row = False
                                for column in range(number_of_columns):
                                    header_list.append(row[column])
                            else:
                                for column in range(number_of_columns):
                                        if "Detailed Status" in header_list[column]:
                                            print row
                                            rowvalue = row[column]
                                            rowvalue = rowvalue.split('@ ')[1]
                                            thistime = datetime.datetime.strptime(rowvalue, '%Y-%m-%d %H:%M:%S' )
                                            stage_doc['_source']['date'] = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                        else:
                                            if "Stage" in header_list[column]:
                                                if row[column] not in ws_doc[wdir]:
                                                    ws_doc[wdir].append(row[column]) 
                                            stage_doc['_source'][header_list[column]] = row[column]
                                b = copy.deepcopy(stage_doc)
                            if b:
                                stage_actions.append(b)
#    for i in stage_actions:
#        print json.dumps(i, indent=1)
#    print json.dumps(ws_doc, indent=1)

    for work, stages in ws_doc.items():
        for stage in stages:
            stagefile = "%s/%s.csv" % (work, stage)
            stagedata_doc = copy.deepcopy(maindoc)
            stagedata_doc['_source']['stage'] = stage
            stagedata_doc['_source']['Workdload'] = work
            stagedata_doc['_source']['file'] = stagefile
            try:
                with open(stagefile) as csvfile:
                    print stagefile
                    readCSV = csv.reader(csvfile, delimiter=',')
                    header_list = []
                    b=""
                    row_count = 0
                    for row in readCSV:
                        if row_count < 2:
                            print "header stuff"
#                            first_header = csvfile.next()
                            if row_count == 0:
                                print "first row"
                                print row
                                first_header_queue = row
#                                first_header = first_header.strip('\n')
#                                first_header_queue = first_header.split(',')
                            if row_count == 1:
                                print "second row"
                                print row
#                                second_header = csvfile.next()
                                second_header_queue = row
#                                second_header = second_header.strip('\n')
#                                second_header_queue = second_header.split(',')
                                second_header_queue.pop(0)

                            print "evaluate"
                            if first_header_queue and second_header_queue:
                                print "process it"
                                for current_header in first_header_queue:
                                    if current_header :
                                        header_list.append(current_header)
                                        previous_header = current_header
                                        new_item = True
                                    else:
                                        if new_item:
                                            header_list.pop()
                                            new_index = first_header_queue.index(current_header)
                                            first_header_queue.insert(new_index,',')
                                            new_item = False
                                        try:
                                            current_header = "%s-%s" % (previous_header, second_header_queue.pop(0))
                                        except:
                                            logging.error("can't set the header var")
    
                                        header_list.append(current_header)

                                print "set it" 
                                number_of_columns = len(header_list)
                            row_count += 1
                        else:
                    #        for row in readCSV:
                                print "row info:"
                     #           print row[0]
#                        for column in rang(number_of_columns):
                           # if "Timestamp" in head_list[column]:
                           #     if new_time > previous_time:
                           #         #format time
                           #         stagedata_doc['_source']['date'] = 
                           # else:
                           #     stagedata_doc['_source']['stagedata_metric'] = [header_list[column]]
                           #     stagedata_doc['_source']['stagedata_value'] = row[column]
            except:
                logging.warn("unabled open file: %s" % stagefile)

#   bluk_import(stage_actions)


    exit()


############################################################################################################


    for dirpath, dirs, files in os.walk("."):	
	for filename in files:
        	fname = os.path.join(dirpath,filename)
        	#for each benchmark capture benchmark metadata and process all pbench data
        	if 'benchmark_config.yaml' in fname:
			bdoc = copy.deepcopy(maindoc)
			p2= multiprocessing.Process(target=t_process_benchmark_data, args=(fname, dirpath, bdoc))
			process2.append(p2)
    for process in process2:
    	process.start()
    for process in process2:
    	try:
        	process.join()
        except:
        	logging.exception("failed")
	

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
                        logging.exception("failed")


                threads2.append(t)
        #start all threads 
        for thread in threads2:
                thread.start()

        #wait for all threads to complete
        for thread in threads2:
                try:
                	thread.join()                
                except: 
                        logging.exception("failed")


def push_bulk_pbench_data_to_es(host_dir, headerdoc):
    for pdirpath, pdirs, pfiles in os.walk(host_dir.strip()):
        for pfilename in pfiles:
            pfname = os.path.join(pdirpath, pfilename)
            if ".csv" in pfname:

                pbenchdoc = copy.deepcopy(headerdoc)
		#print json.dumps(pbenchdoc, indent=1)
                col_ary = []
                actions = []
		a = {}
                first_row = True
		index = False

                pbenchdoc['_source']['host'] = pfname.split("/")[5]
                pbenchdoc['_source']['tool'] = pfname.split("/")[6]
                pbenchdoc['_source']['file_name'] = pfname.split("/")[8]
                #logging.info('proccesing %s' % pbenchdoc['_source']['file_name'])
		starttime_process = datetime.datetime.now()
		with open(pfname) as csvfile:
                    readCSV = csv.reader(csvfile, delimiter=',')
                    for row in readCSV:
                        if first_row:
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
                                    elif 'iostat' in pbenchdoc['_source']['tool']:
                                        iostatdoc = copy.deepcopy(pbenchdoc)
                                        iostatdoc['_source']['device'] = col_ary[col]
                                        iostatdoc['_source']['iostat_value'] = float(row[col])
                                        a = copy.deepcopy(iostatdoc)
				    elif 'mpstat' in pbenchdoc['_source']['tool'] and "cpuall_cpuall.csv" in pbenchdoc['_source']['file_name']:
					mpstat = copy.deepcopy(pbenchdoc)
					mpstat['_source']['cpu_stat'] = col_ary[col]
					mpstat['_source']['cpu_value'] = float(row[col])
					a = copy.deepcopy(mpstat)
				if a:
		                    	actions.append(a)
					index = True
				else:
					index = False
		if index:
			stoptime_process = datetime.datetime.now()
			process_duration = (stoptime_process-starttime_process).total_seconds()
			time.sleep(process_duration)




def bluk_import(a):
    
    actions = copy.deepcopy(a)
    index = True
    while index: 
        try:
            bulk_status = int((es.cat.thread_pool(thread_pool_patterns='write', format=json)).split(" ")[3])
	    wait_counter=1
            #logging.info("waiting for available bulk thread...")

            while bulk_status > 25:
                wait_time = 10 * wait_counter
		#logging.warn("bulk thread pool high(%s), throttling for %s seconds" % (bulk_status, wait_time))
		time.sleep(wait_time)
	        
                if wait_counter == 4:
                    wait_counter = 1 
                else:
                    wait_counter += 1
    
                bulk_status = int((es.cat.thread_pool(thread_pool_patterns='write', format=json)).split(" ")[3])
				
            logging.info('Bulk indexing')
            deque(helpers.parallel_bulk(es, actions, chunk_size=1000, thread_count=1, request_timeout=60), maxlen=0)
            #logging.info("indexing complete...")
	    index = False
    	except Exception as e:
            bulk_status = (es.cat.thread_pool(thread_pool_patterns='write', format=json)).split(" ")[3]
            error_doc = {}
            error_status_ary = []
            error_doc = e.args
            error_type = type(e)
	    try:
	        for i in error_doc:
		    if isinstance(i, list):
                        for j in i:
	        	    if j['index']['status'] not in error_status_ary:
		                error_status_ary.append(j['index']['status'])
	        for i in error_status_ary: 
                        logging.error("Failed to index - Status: %s - %s" % (i, type(e)))
            except:
                logging.error("Failed to index")







if __name__ == '__main__':
    main()
