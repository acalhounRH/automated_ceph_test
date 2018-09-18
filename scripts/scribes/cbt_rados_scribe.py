import yaml, os, time, json, hashlib
import socket, datetime, csv, logging
from datetime import timedelta
import itertools

logger = logging.getLogger("index_cbt")

class rados_transcriber():
    def __init__(self, raw_log, json_log, metadata):
        self.raw_log = raw_log
        self.json_log = json_log
        self.metadata = metadata
        self.mode = metadata['ceph_benchmark_test']['test_config']['mode']
        
    def emit_actions(self):
        
        importdoc = {}
        importdoc["_index"] = "rados-log-indextest1"
        importdoc["_type"] = "radoslogfiledata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
        
        
        with open(self.raw_log) as f:
            header_list = ["Seconds since start", "current Operations", "started", "finished", "avg MB/s",  "cur MB/s", "last lat(s)",  "avg lat(s)"] 
            time_set = False
            placeholder_list = []
            line_count = 0
            if "wrtie" in self.mode:
                result = itertools.islice(f, 4, None)
            elif "read" in self.mode:
                result = itertools.islice(f, 2, None)
                
            for i in result:
                tmp_doc = {}
                i = i.strip()
                if "Total time run:" in i:
                    break
                
                if line_count <=19:
                    value_list = i.split()
                    
                    for index in range(7):
                        value = value_list[index]
                        metric = header_list[index]
                        if "-" in value: value = ""
                        tmp_doc[metric] = value 
                            
                    if time_set:                       
                        current_seconds_since_start = int(tmp_doc["Seconds since start"])
                        cur_time = start_time + timedelta(seconds=current_seconds_since_start)
                        tmp_doc["date"] = cur_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        importdoc["_source"]['ceph_benchmark_test']["test_data"] = tmp_doc
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
                        start_time = mtimestruct + timedelta(seconds=20)
                        sometime = mtimestruct.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        
                        while len(placeholder_list) > 0:
                            current_item = placeholder_list.pop()
                            print json.dumps(current_item, indent=1)
                            current_seconds_since_start = int(current_item["Seconds since start"])
                            cur_time = start_time + timedelta(seconds=current_seconds_since_start)
                            current_item["date"] = cur_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                            importdoc["_source"]['ceph_benchmark_test']["test_data"] = tmp_doc
                            importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                            yield importdoc
                        time_set = True 
                                
class rados_json_transcriber():
    def __init__(self, json_file, start_time, metadata):
        self.json_file = json_file
        self.start_time = start_time
        self.metadata = metadata
        
    def emit_actions(self):
        importdoc = {}
        importdoc["_index"] = "rados-json-indextest1"
        importdoc["_type"] = "radosjsonfiledata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
                                