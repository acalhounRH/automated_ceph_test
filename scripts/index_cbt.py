#! /usr/bin/python

import os, sys, json, time, types, csv, copy, hashlib
import logging, statistics
import datetime
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
import threading
from threading import Thread
from collections import deque
import multiprocessing

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(process)d %(threadName)s: %(levelname)s - %(message)s ')
    
    #check for test id, if not, set generic test id
    if len(sys.argv) > 3:
        test_id = sys.argv[1]
        host = sys.argv[2]
        esport = sys.argv[3]
    else: 
        test_id = "librbdfio-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())

    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        ) 


    for i in process_data_generator():
        print json.dumps(i, indent=1)

#    es_index(es, process_data_generator())
#    streaming_bulk(es, process_data_generator())


##############################################################

def process_data_generator():
    
    object_generator = process_data()

    for obj in object_generator:
        for action in obj.emit_actions():
            yield action

def process_data():
    test_metadata = {}

    #parse CBT achive dir and call process method
    for dirpath, dirs, files in os.walk("."):
        for filename in files:
            fname = os.path.join(dirpath,filename)
            if 'cbt_config.yaml' in fname:
                process_CBT_fiojson_generator = process_CBT_fiojson(dirpath, copy.deepcopy(test_metadata))
                for fiojson_obj in process_CBT_fiojson_generator:
                    yield fiojson_obj
            #for each benchmark capture benchmark metadata and process all data
            if 'benchmark_config.yaml' in fname:
                for line in open(fname, 'r'):
                    line = line.strip()
                    test_metadata[line.split[':'][0]] = line.split[':'][1] 

            if test_metadata['object_size']: test_metadata['object_size'] = int(test_metadata['object_size']) / 1024
               # process_CBT_Pbench_data_generator = process_CBT_Pbench_data(test_directory, test_metadata)
               # for pbench_obj in process_CBT_Pbench_data_generator:
               #     yield pbench_obj 
               # process_CBT_fiologs_generator = process_CBT_fiologs(test_directory, test_metadata)
               # for fiolog_obj in process_CBT_fiologs_generator:
               #     yield fiolog_obj
                

def process_CBT_Pbench_data(tdir, test_metadata):

    #For each host in tools default create pbench scribe object for each csv file
    logging.info('processing data in benchmark %s, mode %s, object size %s' % (benchmarkdoc["_source"]['benchmark'], benchmarkdoc["_source"]['mode'], benchmarkdoc["_source"]['object_size']))
    hosts_dir = "%s/tools-default" % tdir
    for host in os.listdir(hosts_dir):
        host_dir_fullpath = "%s/%s" % (hosts_dir, host) 
    #def push_bulk_pbench_data_to_es(host_dir, headerdoc):
        for pdirpath, pdirs, pfiles in os.walk(host_dir_fullpath.strip()):
            for pfilename in pfiles:
                pfname = os.path.join(pdirpath, pfilename)
                if ".csv" in pfname:
                    metadata = {}
                    metadata["_source"] = test_metadata
                    metadata["_source"]['host'] = pfname.split("/")[5]
                    metadata["_source"]['tool'] = pfname.split("/")[6]
                    metadata["_source"]['file_name'] = pfname.split("/")[8]
                
                    pb_evaluator_generator = pbench_evaluator(csv, metadata)
                    yield pb_evaluator_generator

def process_CBT_fiojson(tdir, test_metadata):
    
    fiojson_evaluator_generator = fiojson_evaluator
    
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath,filename)
            if 'benchmark_config.yaml' in fname:
                for line in open(fname, 'r'):
                    line = line.strip()
                    test_metadata[line.split[':'][0]] = line.split[':'][1]
                    
                test_files = sorted(listdir_fullpath(dirpath), key=os.path.getctime) # get all samples from current test dir in time order
                for file in test_files:
                    if "json_" in file:
                        fiojson_evaluator_generator.add_json_file(file, test_metadata)
                            #fiojson_evaluator_generator = fiojson_evaluator(file, test_metadata)
                            #yield fiojson_evaluator_generator
                
    for import_obj in fiojson_evaluator_generator.get_fiojson_importers():
        yield import_obj
        
    yield fiojson_evaluator_generoator

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def process_CBT_fiologs(tdir, test_metadata):


        # get all samples from current test dir in time order
    test_files = sorted(listdir_fullpath(tdir), key=os.path.getctime)

        #for each fio log file capture test time in json file then yield evaluator object
    for file in test_files:
    	if ("_iops" in file) or ("_lat" in file):
        #if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):
            #fiologdoc = copy.deepcopy(headerdoc)
            metadata["_source"] = test_metadata
            jsonfile = "%s/json_%s.%s" % (tdir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
            metadata["_source"]['host'] = os.path.basename(file).split('log.', 1)[1]

            fiolog_evaluator_generator = fiologevaluator(file, jsonfile, metadata)
            yield fiolog_evaluator_generator

###############################CLASS DEF##################################
class import_fiojson:

    def __init__(self, json_file, metadata):
        self.metadata = metadata
        self.json_file = json_file
        
    def emit_actions(self):
        importdoc = {}
        importdoc["_index"] = "cbt_librbdfio-json-index"
        importdoc["_type"] = "librbdfiojsondata"
        importdoc["_op_type"] = "create"
        importdoc = self.metadata

        json_doc = json.load(open(self.json_file))
        #create header dict based on top level objects
        importdoc['date'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.localtime(json_doc['timestamp']))
        importdoc['global_options'] = json_doc['global options']
        importdoc['global_options']['bs'] = ( int(importdoc['global_options']['bs'].strip('B')) / 1024)
        importdoc['timestamp_ms'] = json_doc['timestamp_ms']
        importdoc['timestamp'] = json_doc['timestamp']
        importdoc['fio_version'] = json_doc['fio version']
        importdoc['time'] = json_doc['time']

        for job in json_doc['jobs']:
            importdoc['_source']['job'] = job
            #XXX: TODO need to add total_iops for all jons in current record
            importdoc['_source']['total_iops'] = int(importdoc['_source']['job']['write']['iops']) + int(importdoc['_source']['job']['read']['iops'])
            importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
            yield importdoc
    
class fiojson_evaluator:
    def __init__(self):
        self.json_data_list = []
        self.iteration_list = []
        self.operation_list = []
        self.block_size_list = []
        self.sumdoc = {}
        
    def add_json_file(self, json_file, metadata):
        json_data = {}
        json_data['jfile'] = json_file
        json_data['metadata'] = metadata 
        self.json_data_list.append(json_data)
        
    def calculate_iops_sum(self):
        for json_data in self.json_data_list:
            iteration = json_data['metadata']['iteration']
            op_size = json_data['metadata']['op_size']
            mode = json_data['metadata']['mode']
            
            if iteration not in self.iteration_list: self.iteration_list.append(iteration)
            if op_size not in self.block_size_list: self.block_size_list.append(op_size)
            if mode not in self.operation_list: self.operation_list.append(mode)
            
            json_doc = json.load(open(json_data['jfile']))
            
            #set time
            
            #get measurements
            for job in json_doc['jobs']:
                self.sumdoc[iteration][mode][op_size]['write'] += job.write.iops
                self.sumdoc[iteration][mode][op_size]['read'] += job.read.iops
        
    def get_fiojson_importers():
        
        for json_file in self.json_data_list:
            fiojson_import_generator = import_fiojson(json_file['jfile'], json_file['metadata'])
            yield fioson_import_generator
            
    def emit_actions(self):
        
        importdoc = {}
        importdoc["_index"] = "cbt_librbdfio-summary-index"
        importdoc["_type"] = "librbdfiosummarydata"
        importdoc["_op_type"] = "create"
        
        self.calculate_iops_sum()
        
        for oper in self.operation_list:
            for obj_size in self.block_size_list:
                waver_ary = []
                raver_ary = []
                total_ary = []
                averdoc = {}
                averdoc['object_size'] = obj_size # set document's object size
                averdoc['test_id'] = test_id
                averdoc['operation'] = oper # set documents operation
                firstrecord = 'false'
                calcuate_percent_std_dev = False
                for itera in self.iteration_list: # 
                    try:
                        waver_ary.append(self.sumdoc[itera][oper][obj_size]['write'])
                        raver_ary.append(self.sumdoc[itera][oper][obj_size]['read'])
        
                        if firstrecord is 'false':
                            averdoc['date'] = newdoc[itera][oper][obj_size]['date']
                            firstrecord = 'true'
                    except:
                        pass
                    
                #print "##################average##################"
                read_average = (sum(raver_ary)/len(raver_ary))
                if read_average > 0.0:
                    averdoc['read-iops'] = read_average
                    if len(raver_ary) > 1:
                        calcuate_percent_std_dev = True
                else:
                    averdoc['read-iops'] = 0
        
                write_average = (sum(waver_ary)/len(waver_ary))
                if write_average > 0.0:
                    print "process write %s" % len(waver_ary)
                    averdoc['write-iops'] = write_average
                    if len(waver_ary) > 1:
                        calcuate_percent_std_dev = True 
                else:
                        averdoc['write-iops'] = 0
        
                averdoc['total-iops'] = (averdoc['write-iops'] + averdoc['read-iops'])
                
                if calcuate_percent_std_dev:
                    if "read" in oper:
                        averdoc['std-dev-%s' % obj_size] = round(((statistics.stdev(raver_ary) / read_average) * 100), 3)
                    elif "write" in oper: 
                        averdoc['std-dev-%s' % obj_size] = round(((statistics.stdev(waver_ary) / write_average) * 100), 3)
                    elif "randrw" in oper:
                        averdoc['std-dev-%s' % obj_size] = round((((statistics.stdev(raver_ary) + statistics.stdev(waver_ary)) / averdoc['total-iops'])* 100), 3)
                #print json.dumps(averdoc, indent=1) 
                #res = es.index(index="cbt_librbdfio-summary-index", doc_type='fiologfile', body=averdoc)
                importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                yield averdoc
         
            
class fiolog_evaluator:
    
    def __init__(self, csv_file, json_file, metadata):
        self.csv_file = csv_file
        self.json_file = json_file
        self.metadata = metadata

    def emit_actions():
        
        importdoc = {}
        importdoc["_index"] = "fio-log-index"
        importdoc["_type"] = "librbdfiologdata"
        importdoc["_op_type"] = "create"
        importdoc = self.metadata
        
        jsondoc = json.load(open(self.json_file))
        test_time_ms = long(jsondoc['timestamp_ms'])
        test_duration_ms = long(jsondoc['global options']['runtime']) * 1000
        start_time = test_time_ms - test_duration_ms
    
        importdoc["_source"]["test_data"]['file'] = os.path.basename(self.csv_file)
        with open(self.csv_file) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in (readCSV):
                ms = float(row[0]) + float(start_time)
                newtime = datetime.datetime.fromtimestamp(ms / 1000.0)
                importdoc["_source"]['date'] = newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                importdoc["_source"]["test_data"]['value'] = int(row[1])
                importdoc["_source"]["test_data"]['data direction'] = row[2]
                
                importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                yield importdoc  # XXX: TODO change to yield a

class pbench_evaluator:

    def __init__(self, csv_file, metadata):
        self.csv_file = csv_file
        self.metadata = metadata

    def emit_actions(self):
        importdoc = {}
        importdoc["_index"] = "pbench"
        importdoc["_type"] = "pbenchdata"
        importdoc["_op_type"] = "create"
        importdoc['_source'] = self.metadata
    
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
                        importdoc['_source']['test_data'] = {}
                        if 'timestamp_ms' in col_ary[col]:
                            ms = float(row[col])
                            thistime = datetime.datetime.fromtimestamp(ms / 1000.0)
                            importdoc['_source']['date'] = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        else:
                            if 'pidstat' in importdoc['_source']['tool']:

                                pname = col_ary[col].split('/')[-1]
                                if "ceph-osd" in pname or "ceph-mon" in pname or "ceph-mgr" in pname:
                                    pid = col_ary[col].split('-', 1)[0]
                                    importdoc['_source']['test_data']['process_name'] = pname
                                    importdoc['_source']['test_data']['process_pid'] = pid
                                    importdocc['_source']['test_data']['process_value'] = float(row[col])
                                    a = importdoc
                            elif 'sar' in importdoc['_source']['tool'] and "network_" in importdoc['_source']['file_name']:
                                importdoc['_source']['test_data']['network_interface'] = col_ary[col]
                                importdoc['_source']['test_data']['network_value'] = float(row[col])
                                a = importdoc
                            elif 'sar' in importdoc['_source']['tool'] and "memory_" in importdoc['_source']['file_name']:
                                sardoc['_source']['test_data']['memory_stat'] = col_ary[col]
                                sardoc['_source']['test_data']['memory_value'] = float(row[col])
                                a = importdoc
                            # elif 'sar' in pbenchdoc['_source']['tool'] and "per_cpu_" in pbenchdoc['_source']['file_name']:
                            #    sardoc['_source']['sarcpu_stat'] = col_ary[col]
                            #    sardoc['_source']['sarcpu_value'] = float(row[col])
                            #    a = copy.deepcopy(sardoc)
                            elif 'iostat' in importdoc['_source']['tool']:
                                importdoc['_source']['test_data']['device'] = col_ary[col]
                                importdoc['_source']['test_data']['iostat_value'] = float(row[col])
                                a = importdoc
                            elif 'mpstat' in importdoc['_source']['tool'] and "cpuall_cpuall.csv" in importdoc['_source']['file_name']:
                                importdoc['_source']['test_data']['cpu_stat'] = col_ary[col]
                                importdoc['_source']['test_data']['cpu_value'] = float(row[col])
                                a = importdoc
                        if a:
                                importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                                yield a 

###############################PY_ES_BULK##################################

def streaming_bulk(es, actions):
    """
    streaming_bulk(es, actions, errorsfp)
     Arguments:
         es - An Elasticsearch client object already constructed
        actions - An iterable for the documents to be indexed
        errorsfp - A file pointer for where to write 400 errors
     Returns:
         A tuple with the start and end times, the # of successfully indexed,
        duplicate, and failed documents, along with number of times a bulk
        request was retried.
    """
     # These need to be defined before the closure below. These work because
    # a closure remembers the binding of a name to an object. If integer
    # objects were used, the name would be bound to that integer value only
    # so for the retries, incrementing the integer would change the outer
    # scope's view of the name.  By using a Counter object, the name to
    # object binding is maintained, but the object contents are changed.
    actions_deque = deque()
    actions_retry_deque = deque()
    retries_tracker = Counter()
    def actions_tracking_closure(cl_actions):
        for cl_action in cl_actions:
            assert '_id' in cl_action
            assert '_index' in cl_action
            assert '_type' in cl_action
            assert _op_type == cl_action['_op_type']
            actions_deque.append((0, cl_action))   # Append to the right side ...
            yield cl_action
            # if after yielding an action some actions appear on the retry deque
            # start yielding those actions until we drain the retry queue.
            backoff = 1
            while len(actions_retry_deque) > 0:
                time.sleep(calc_backoff_sleep(backoff))
                retries_tracker['retries'] += 1
                retry_actions = []
                # First drain the retry deque entirely so that we know when we
                # have cycled through the entire list to be retried.
                while len(actions_retry_deque) > 0:
                    retry_actions.append(actions_retry_deque.popleft())
                for retry_count, retry_action in retry_actions:
                    actions_deque.append((retry_count, retry_action))   # Append to the right side ...
                    yield retry_action
                # if after yielding all the actions to be retried, some show up
                # on the retry deque again, we extend our sleep backoff to avoid
                # pounding on the ES instance.
                backoff += 1
            
    beg, end = time.time(), None
    successes = 0
    duplicates = 0
    failures = 0
     # Create the generator that closes over the external generator, "actions"
    generator = actions_tracking_closure(actions)
    streaming_bulk_generator = helpers.streaming_bulk(
           es, generator, raise_on_error=False,
           raise_on_exception=False, request_timeout=_request_timeout)
    for ok, resp_payload in streaming_bulk_generator:
       retry_count, action = actions_deque.popleft()
       try:
           resp = resp_payload[_op_type]
           status = resp['status']
       except KeyError as e:
           assert not ok
           # resp is not of expected form
           print(resp)
           status = 999
#        else:
#            assert action['_id'] == resp['_id']
       if ok:
           successes += 1
       else:
           if status == 409:
               if retry_count == 0:
                   # Only count duplicates if the retry count is 0 ...
                   duplicates += 1
               else:
                   # ... otherwise consider it successful.
                   successes += 1
           elif status == 400:
#                doc = {
#                        "action": action,
#                        "ok": ok,
#                        "resp": resp,
#                        "retry_count": retry_count,
#                        "timestamp": tstos(time.time())
#                        }
#                jsonstr = json.dumps(doc, indent=4, sort_keys=True)
#                print(jsonstr, file=errorsfp)
#               errorsfp.flush()
               failures += 1
           else:
               # Retry all other errors
               print(resp)
               actions_retry_deque.append((retry_count + 1, action))
    end = time.time()
    assert len(actions_deque) == 0
    assert len(actions_retry_deque) == 0
    return (beg, end, successes, duplicates, failures, retries_tracker['retries'])
 
 
if __name__ == '__main__':
    main()





