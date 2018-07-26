#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import xmltodict
import logging
import datetime
from time import gmtime, strftime
from datetime import timedelta
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
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s - %(message)s ')
    maindoc = {}
    process2 = []
    maindoc["_index"] = "cosbench"
    maindoc["_type"] = "cosbenchdata"
    maindoc["_source"] = {}
    
    test_id = ""
    host = ""
    port = ""
    workload_list = []

    usage = """ 
            Usage:
                evaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>
                
                -t or --test_id - test identifier
                -h or --host - Elasticsearch host ip or hostname
                -p or --port - Elasticsearch port (elasticsearch default is 9200)
                -w or --workloads - a list of workloads that should be imported 
            """

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
        logging.info(usage)
#        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
        exit ()

    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        ) 

    #if the pbench index doesnt exist create index
    if not es.indices.exists("cosbench"):
        request_body = {"settings" : {"refresh_interval": "10s", "number_of_replicas": 0}}
        res = es.indices.create(index="cosbench", body=request_body)
        logging.debug("response: '%s' " % (res))
    
    
    run_history = {}
    run_actions = []
    first_row = True
    logging.info("process run-history file")
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
    
    bluk_import(run_actions)
    
    logging.info("Process selected workload stage reports")
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
                    stage_doc['_source']['Workload'] = wdir
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
                                            for i in xrange(header_list.index("Detailed Status"), len(row)):
                                                detailed_status = row[i]
                                                status, time = detailed_status.split(' @ ')
                                                thistime = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S' )
                                                thistime = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                                fulldstatus = "Detailed Status - %s" % status
                                                if "launching" in status or "aborted" in status or "failed" in status or "terminated" in status:
                                                    stage_doc['_source']['date'] = thistime
                                                    stage_doc['_source'][fulldstatus] = thistime
                                                else:
                                                    stage_doc['_source'][fulldstatus] = thistime
                                        elif "Status" in header_list[column]:
                                            if "finished" in row[column]:
                                                stage_doc['_source']['StatusID'] = 0
                                            elif "failed" in row[column]:
                                                stage_doc['_source']['StatusID'] = 3
                                            elif "cancelled" in row[column]:
                                                stage_doc['_source']['StatusID'] = 2
                                            elif "terminated" in row[column]:
                                                stage_doc['_source']['StatusID'] = 1
                                            else:
                                                stage_doc['_source']['StatusID'] = 4
        
                                            stage_doc['_source'][header_list[column]] = row[column]
                                        else:
                                            if "Stage" in header_list[column]:
                                                if row[column] not in ws_doc[wdir]:
                                                    ws_doc[wdir].append(row[column]) 
                                            stage_doc['_source'][header_list[column]] = row[column]
                              
                                with open("%s/workload-config.xml" % stage_doc['_source']['Workload']) as fd:
                                    workloadxmldoc = xmltodict.parse(fd.read())

                                try: #xml has stage list, find all
                                    for j in workloadxmldoc["workload"]["workflow"]["workstage"]:
                                        if j["@name"] in stage_doc['_source']["Stage"]:
                                            stage_doc['_source']['Workers'] = j["work"]["@workers"]
                                except: #no stage list, only one stage.
                                    print workloadxmldoc["workload"]["workflow"]["workstage"]["@name"]
                                    if workloadxmldoc["workload"]["workflow"]["workstage"]["@name"] in stage_doc['_source']["Stage"]:
                                        stage_doc['_source']['Workers'] = workloadxmldoc["workload"]["workflow"]["workstage"]["work"]["@workers"]
                                        
                                b = copy.deepcopy(stage_doc)

                            if b:
                                stage_actions.append(b)
#    for i in stage_actions:
#        print json.dumps(i, indent=1)
    
#   print json.dumps(ws_doc, indent=1)
    
    bluk_import(stage_actions)

    logging.info("Process Stage data")
    for work, stages in ws_doc.items():
        for stage in stages:
            set_starttime = True
            stage_status = []
            process_stage = True
            for i in stage_actions: 
                if stage in  i["_source"]['Stage'] and work in i["_source"]['Workload']:
                    stage_status.append(i['_source']['Status'])
                    if set_starttime: 
                        stage_starttime = i["_source"]['date']
                        current_date = datetime.datetime.strptime(stage_starttime, '%Y-%m-%dT%H:%M:%S.%fZ' )
                        previous_time = current_date.strftime('%H:%M:%S')
                        set_starttime = False

            valid_stagedata = True
            if process_stage:            
                stagefile = "%s/%s.csv" % (work, stage)
                stagedata_doc = copy.deepcopy(maindoc)
                stagedata_doc['_source']['stage'] = stage
                stagedata_doc['_source']['Workload'] = work
                workID = work.split("-")[0]
                stagedata_doc['_source']['Workload ID'] = int(workID.strip('w'))

                stagedata_doc['_source']['file'] = stagefile
                stagedata_actions = []
                logging.info("Processing %s from workload: %s" % (stage, work))
                try:
                    with open(stagefile) as csvfile:
                        readCSV = csv.reader(csvfile, delimiter=',')
                        header_list = []
                        b=""
                        row_count = 0
                        first_header_queue = []
                        second_header_queue = []
                        for row in readCSV:
                            if row_count < 2:
                                if row_count == 0:
                                    first_header_queue = row
    
                                if row_count == 1:
                                    second_header_queue = row
                                    second_header_queue.pop(0)

                                if first_header_queue and second_header_queue: 
                                    for current_header in first_header_queue:
                                        if current_header :
                                            if "Timestamp" in current_header:
                                                header_list.append(current_header)
                                            else:
                                                full_header = "%s @ %s" % (current_header, second_header_queue.pop(0))
                                                header_list.append(full_header)
                                            previous_header = current_header
                                        else:
                                            try:
                                                current_header = "%s @ %s" % (previous_header, second_header_queue.pop(0))
                                            except:
                                                logging.error("can't set the header var")
    
                                            header_list.append(current_header)
                                    number_of_columns = len(header_list)
                                row_count += 1
                            else:
                                if len(row) == len(header_list):
                                    for column in range(number_of_columns):
                                        if "Timestamp" in header_list[column]:
                                            current_time = row[column]
                                            if previous_time > current_time:
                                                current_date += timedelta(days=1)
                                        
                                            str_current_date = current_date.strftime('%Y-%m-%d')
                                            new_datetime = "%s %s" % (str_current_date, current_time)
                                            current_datetime = datetime.datetime.strptime(new_datetime, '%Y-%m-%d %H:%M:%S' )
                                            current_datetime = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                            previous_time = current_time
                                            stagedata_doc['_source']['date'] = current_datetime 
                                        else:
                                            header_name = header_list[column]
                                            try:
                                                metric_type, op_type = header_name.split(" @ ")
                                                stagedata_doc['_source']['op-type'] = op_type
                                                stagedata_doc['_source']['metric-type'] = metric_type 
                                                stagedata_doc['_source']['stagedata_metric'] = header_list[column]
                                            except:
                                                print header_name
    
                                            if "%"in row[column]:
                                                sd_value = row[column].strip('%')
                                            elif "N/A" in row[column]:
                                                sd_value = 0 
                                            else:
                                                sd_value = row[column] 
                                            stagedata_doc['_source']['stagedata_value'] = float(sd_value)
                                            b = copy.deepcopy(stagedata_doc)
                                    
                                        if b:
                                            stagedata_actions.append(b)
                                else:
                                    logging.error("Corrupted data found, omitting data point")
                        
                    bluk_import(stagedata_actions)

                except Exception as e :
                    logging.error(e)

#   bluk_import(stage_actions)
#    for i in stagedata_actions:
#        print json.dumps(i, indent=1)


############################################################################################################

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
		logging.warn("bulk thread pool high(%s), throttling for %s seconds" % (bulk_status, wait_time))
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
