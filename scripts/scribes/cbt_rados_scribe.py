import yaml, os, time, json, hashlib
import socket, datetime, csv, logging, copy
from datetime import timedelta
from collections import defaultdict
import itertools
import statistics

logger = logging.getLogger("index_cbt")

class rados_transcriber():
    def __init__(self, raw_log, metadata):
        self.raw_log = raw_log
        self.metadata = metadata
        self.mode = metadata['ceph_benchmark_test']['test_config']['mode']
        
        file_name = os.path.basename(self.raw_log)
        dir_name = os.path.dirname(self.raw_log)
        json_file = "json_%s" % file_name 
        self.json_log = "%s/%s" % (dir_name, json_file)
        junk, self.rados_instance, self.host = file_name.split(".", 2)
        
    def emit_actions(self):
        
        importdoc = {}
        importdoc["_index"] = "rados-log-indextest1"
        importdoc["_type"] = "radoslogfiledata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
        
        importdoc["_source"]['ceph_benchmark_test']['common']['hardware'] = {"host": self.host}
        #importdoc["_source"]['ceph_benchmark_test']["test_data"] = {}
        #importdoc["_source"]['ceph_benchmark_test']["test_data"]['rados_instance'] = rados_instance
        
        logger.debug("Indexing %s" % self.raw_log)
        with open(self.raw_log) as f:
            header_list = ["Seconds since start", "current Operations", "started", "finished", "avg MB/s",  "cur MB/s", "last lat(s)",  "avg lat(s)"] 
            time_set = False
            placeholder_list = []
            line_count = 0
            if "write" in self.mode:
                result = itertools.islice(f, 4, None)
            elif "read" in self.mode:
                result = itertools.islice(f, 2, None)
                
            for i in result:
                importdoc["_source"]['ceph_benchmark_test']["test_data"] = {}
                importdoc["_source"]['ceph_benchmark_test']["test_data"]['rados_instance'] = self.rados_instance
                tmp_doc = {}
                i = i.strip()
                if "Total time run:" in i:
                    break
                
                if line_count <=19:
                    value_list = i.split()
                    
                    for index in range(7):
                        value = value_list[index]
                        metric = header_list[index]
                        if "-" in value: value = 0
                        tmp_doc[metric] = float(value) 
                            
                    if time_set:                       
                        current_seconds_since_start = int(tmp_doc["Seconds since start"])
                        cur_time = start_time + timedelta(seconds=current_seconds_since_start)
                        importdoc["_source"]["date"] = cur_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        importdoc["_source"]['ceph_benchmark_test']['test_data']['rados_logs'] = tmp_doc
                        importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                        yield importdoc 
                    else:
                        placeholder_list.append(tmp_doc)
                                  
                    line_count += 1
                else:
                    if line_count >20:
                        line_count = 0
                    else:
                        line_count += 1 
                        
                    if not time_set:
                        mdate, mtime = i.split()[:2]
                        time_mark = "%sT%s" % (mdate, mtime)
                        mtimestruct = datetime.datetime.strptime(time_mark, '%Y-%m-%dT%H:%M:%S.%f')
                        start_time = mtimestruct - timedelta(seconds=20)
                        
                        sometime = mtimestruct.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        
                        while len(placeholder_list) > 0:
                            current_item = placeholder_list.pop()
                            current_seconds_since_start = int(current_item["Seconds since start"])
                            cur_time = start_time + timedelta(seconds=current_seconds_since_start)
                            importdoc["_source"]["date"] = cur_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                            importdoc["_source"]['ceph_benchmark_test']['test_data']['rados_logs'] = current_item
                            importdoc["_id"] = hashlib.md5(str(importdoc).encode()).hexdigest()
                            yield importdoc
                        time_set = True 
                                
class rados_json_transcriber():
    def __init__(self, json_file, start_time, metadata):
        self.json_file = json_file
        self.start_time = start_time
        self.metadata = metadata
        
    def emit_actions(self):
        
        logger.debug("Indexing %s" % self.json_file)
        
        importdoc = {}
        importdoc["_index"] = "rados-json-indextest1"
        importdoc["_type"] = "radosjsonfiledata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
        importdoc["_source"]['date'] = self.start_time
        with open(self.json_file, 'r') as myfile:
            data=myfile.read()
        
        tmpdoc = {
            "rados_json": json.loads(data)
            }
        importdoc["_source"]['ceph_benchmark_test']['test_data'] = tmpdoc
        importdoc["_id"] = hashlib.md5(str(importdoc).encode()).hexdigest()
        yield importdoc 
        
                         
class rados_json_results_transcriber:
    
    def __init__(self, metadata):
        self.json_data_list = []
        self.iteration_list = []
        self.operation_list = []
        self.block_size_list = []
        self.sumdoc = defaultdict(dict)    
        self.metadata = metadata
        
    def add_json_file(self, json_file, metadata):
        json_data = {}
        json_data['jfile'] = json_file
        file_time = os.path.getmtime(json_file)
        json_data['start_time'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(file_time))
        json_data['metadata'] = metadata 
        self.json_data_list.append(json_data)
        
    def calculate_iops_sum(self):
        
        for json_data in self.json_data_list:
            iteration = json_data['metadata']['ceph_benchmark_test']['test_config']['iteration']
            op_size = json_data['metadata']['ceph_benchmark_test']['test_config']['op_size']
            mode = json_data['metadata']['ceph_benchmark_test']['test_config']['mode']
            
            if iteration not in self.iteration_list: self.iteration_list.append(iteration) 
            if mode not in self.operation_list: self.operation_list.append(mode)
            if op_size not in self.block_size_list: self.block_size_list.append(op_size)
            
        for iteration in self.iteration_list:
            self.sumdoc[iteration] = {}
            for mode in self.operation_list:
                self.sumdoc[iteration][mode] = {}
                for op_size in self.block_size_list:
                    self.sumdoc[iteration][mode][op_size] = {}
                    
        for json_data in self.json_data_list:
            json_doc = json.load(open(json_data['jfile']))
            
            iteration = json_data['metadata']['ceph_benchmark_test']['test_config']['iteration']
            op_size = json_data['metadata']['ceph_benchmark_test']['test_config']['op_size']
            mode = json_data['metadata']['ceph_benchmark_test']['test_config']['mode']
            
            if not self.sumdoc[iteration][mode][op_size]:
                self.sumdoc[iteration][mode][op_size]['date'] = json_data['start_time']
                self.sumdoc[iteration][mode][op_size]['average_iops'] = 0
                
            self.sumdoc[iteration][mode][op_size]['average_iops'] += int(json_data['metadata']['ceph_benchmark_test']['test_data']['rados_json']['Average IOPS'])
        
    def emit_rados_json_files(self):
        
        for json_file in self.json_data_list: 
            #json_metadata = {}
            json_metadata = json_file['metadata']
            file = json_file['jfile']
            start_time = json_file['start_time']
            
            rados_json_transcriber_obj = rados_json_transcriber(file, start_time, json_metadata)
            yield rados_json_transcriber_obj
        
    def emit_actions(self):
        importdoc = {}
        importdoc["_index"] = "cbt_radosbench-summary-index"
        importdoc["_type"] = "radosbenchsummarydata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
        
        tmp_doc = {}
        
        self.calculate_iops_sum()
        
        for oper in self.operation_list:
            for obj_size in self.block_size_list:
                aver_ary = []
                total_ary = []
                tmp_doc = {}
                tmp_doc['object_size'] = obj_size # set document's object size
                tmp_doc['operation'] = oper # set documents operation
                firstrecord = True
                calcuate_percent_std_dev = False
                for itera in self.iteration_list: # 
                    aver_ary.append(self.sumdoc[itera][oper][obj_size]['average_iops'])
    
                    if firstrecord:
                        importdoc["_source"]['date'] = self.sumdoc[itera][oper][obj_size]['date']
                        firstrecord = True
        
                average = statistics.mean(aver_ary)
                if average > 0.0:
                    tmp_doc['average_iops'] = average
                    if len(aver_ary) > 1:
                        calcuate_percent_std_dev = True 
                else:
                    tmp_doc['average_iops'] = 0
                    
                tmp_doc['total-iops'] = tmp_doc['average_iops']
                
                if calcuate_percent_std_dev:
                    tmp_doc['std-dev-%s' % obj_size] = round(((statistics.stdev(aver_ary) / average) * 100), 3)
            
                importdoc["_source"]['ceph_benchmark_test']['test_data'] = tmp_doc
                importdoc["_id"] = hashlib.md5(str(importdoc).encode()).hexdigest()
                yield importdoc   
        
        
        