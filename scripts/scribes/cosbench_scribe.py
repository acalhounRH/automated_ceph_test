
import os, sys, json, time, types, csv, copy, hashlib
import xmltodict
import logging
import datetime
from time import gmtime, strftime
from datetime import timedelta

logger = logging.getLogger("index_cosbench")

class cosbench_runhistory_transcriber():
    def __init__(self, test_id, file, workload_list):
        
        self.test_id = test_id
        self.run_history_file = file 
        self.workload_list = workload_list
        
    def emit_actions(self):
        
        first_row = True
        logger.info("process run-history file")
        with open(self.run_history_file) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            header_list = []
            counter = 0
            for row in readCSV:
                run_history = {'_index': 'cosbench_runhistory_index',
                               '_type': "cosbench_runhistory",
                               '_op_type': 'create',
                               '_source': {
                                   'test_id': self.test_id
                                   }
                               }
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
                    
                            #a = copy.deepcopy(run_history
                        
                    if  run_history['_source']['Workload ID'] in self.workload_list:
                        run_history['_id'] = hashlib.md5(json.dumps(run_history)).hexdigest()
                        yield run_history 
                
class cosbench_workload_transcriber():
    def __init__(self, test_id, archive_dir, workload_list):
        self.archive_dir = archive_dir
        self.test_id = test_id
        self.ws_doc = {}
        self.workload_list = workload_list
        self.workload_doc_list = []
        
    def emit_actions(self):
        logger.info("Process selected workload stage reports")
        
        for dirpath, dirs, files in os.walk("."):
            for wdir in dirs:
                if wdir.startswith("w"):
                    wdirID = wdir.split("-")[0]
                    wdirID = wdirID.strip('w')
                    if int(wdirID) in self.workload_list:
                        #workload_doc = copy.deepcopy(maindoc)
                        self.ws_doc[wdir] = []
                        #workload_doc['_source']['Workload ID'] = int(wdirID)
                        #workload_doc['_source']['Workload'] = wdir
                        with open("%s/%s.csv" % (wdir, wdir)) as csvfile:
                            readCSV = csv.reader(csvfile, delimiter=',')
                            header_list = []
                            first_row = True
                            b = ""
                            for row in readCSV:
                                workload_doc = {'_index': 'cosbench_workload_index',
                                             '_type': "cosbench_workload",
                                             '_op_type': 'create',
                                             '_source': {
                                                 'Workload ID': int(wdirID),
                                                 'Workload': wdir,
                                                 'test_id': self.test_id
                                                 } 
                                            }
                                
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
                                                    workload_doc['_source']['date'] = thistime
                                                    workload_doc['_source'][fulldstatus] = thistime
                                                else:
                                                    workload_doc['_source'][fulldstatus] = thistime
                                        elif "Status" in header_list[column]:
                                            if "finished" in row[column]:
                                                workload_doc['_source']['StatusID'] = 0
                                            elif "failed" in row[column]:
                                                workload_doc['_source']['StatusID'] = 3
                                            elif "cancelled" in row[column]:
                                                workload_doc['_source']['StatusID'] = 2
                                            elif "terminated" in row[column]:
                                                workload_doc['_source']['StatusID'] = 1
                                            else:
                                                workload_doc['_source']['StatusID'] = 4
        
                                            workload_doc['_source'][header_list[column]] = row[column]
                                        else:
                                            if "Stage" in header_list[column]:
                                                if row[column] not in self.ws_doc[wdir]:
                                                    self.ws_doc[wdir].append(row[column]) 
                                                    
                                            workload_doc['_source'][header_list[column]] = row[column]
                                  
                                    with open("%s/workload-config.xml" % workload_doc['_source']['Workload']) as fd:
                                        workloadxmldoc = xmltodict.parse(fd.read())
        
                                    #xml has stage list, find all
                                    if isinstance(workloadxmldoc["workload"]["workflow"]["workstage"], list):
                                        for j in workloadxmldoc["workload"]["workflow"]["workstage"]:
                                            if j["@name"] in workload_doc['_source']["Stage"]:
                                                if isinstance(j["work"], list):
                                                    workload_doc['_source']['Workers'] = j["work"][0]["@workers"]
                                                else:
                                                    workload_doc['_source']['Workers'] = j["work"]["@workers"]
                                                    
                                    else: #no stage list, only one stage.
                                        #print (workloadxmldoc["workload"]["workflow"]["workstage"]["@name"])
                                        if workloadxmldoc["workload"]["workflow"]["workstage"]["@name"] in workload_doc['_source']["Stage"]:
                                            workload_doc['_source']['Workers'] = workloadxmldoc["workload"]["workflow"]["workstage"]["work"]["@workers"]
                                    
                                    workload_doc["_id"] = hashlib.md5(json.dumps(workload_doc)).hexdigest()
                                    self.workload_doc_list.append(workload_doc)
                                    yield workload_doc
        
class cosbench_stage_transcriber():
    def __init__(self, test_id, ws_doc, workload_doc_list):
        self.test_id = test_id
        self.workload_stage_dict = ws_doc
        self.workload_doc_list = workload_doc_list 
        
    def emit_actions(self):
        logger.info("Process Stage data")
        for work, stages in self.workload_stage_dict.items():
            for stage in stages:
                set_starttime = True
                stage_status = []
                process_stage = True
                for i in self.workload_doc_list: 
                    if stage in  i["_source"]['Stage'] and work in i["_source"]['Workload']:
                        stage_status.append(i['_source']['Status'])
                        if set_starttime: 
                            stage_starttime = i["_source"]['date']
                            current_date = datetime.datetime.strptime(stage_starttime, '%Y-%m-%dT%H:%M:%S.%fZ' )
                            previous_time = current_date.strftime('%H:%M:%S')
                            set_starttime = False
    
                valid_stagedata = True
                if process_stage:            
                    stagefile = "%s/%s.csv" % (os.path.abspath(work), stage)
                    #stagedata_doc = copy.deepcopy(maindoc)
                    stagedata_doc = {"_index": "cosbench_stage_index",
                                     "_type": "cosbench_stage",
                                     "_op_type": "create",
                                     "_source": {
                                         "test_id": self.test_id,
                                         "stage": "",
                                         "Workload": ""
                                         }
                                     }
                    stagedata_doc['_source']['stage'] = stage
                    stagedata_doc['_source']['Workload'] = work
                    workID = work.split("-")[0]
                    stagedata_doc['_source']['Workload ID'] = int(workID.strip('w'))
    
                    stagedata_doc['_source']['file'] = stagefile
                    stagedata_actions = []
                    logger.info("Processing %s from workload: %s" % (stage, work))
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
                                                    logger.error("can't set the header var")
        
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
                                                if "@" in header_name:
                                                    metric_type, op_type = header_name.split(" @ ")
                                                    stagedata_doc['_source']['op-type'] = op_type
                                                    stagedata_doc['_source']['metric-type'] = metric_type 
                                                    stagedata_doc['_source']['stagedata_metric'] = header_list[column]
        
                                                if "%"in row[column]:
                                                    sd_value = row[column].strip('%')
                                                elif "N/A" in row[column]:
                                                    sd_value = 0 
                                                else:
                                                    sd_value = row[column] 
                                                stagedata_doc['_source']['stagedata_value'] = float(sd_value)
                                                
                                                b = copy.deepcopy(stagedata_doc)
                                                b['_id'] = hashlib.md5(json.dumps(b)).hexdigest()
                                                yield b
                                    else:
                                        logger.error("Corrupted data found, omitting data point")
                            
#                         bulk_import(stagedata_actions)
#                         yield stagedata_actions
    
                    except Exception as e :
                        logger.error(e)