
import yaml, os, time, json, hashlib
import socket, datetime, csv, logging

logger = logging.getLogger("index_cbt")

class fiolog_transcriber:
    
    def __init__(self, csv_file, json_file, metadata):
        self.csv_file = csv_file
        self.json_file = json_file
        self.metadata = metadata

    def emit_actions(self):
        
        importdoc = {}
        importdoc["_index"] = "fio-log-indextest1"
        importdoc["_type"] = "librbdfiologdata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
        
        #logger.debug("Indexing %s" % self.csv_file)
        jsondoc = json.load(open(self.json_file))
        test_time_ms = long(jsondoc['timestamp_ms'])
        test_duration_sec = jsondoc['global options']['runtime']
        try:
            if "S" in test_duration_sec: 
                test_duration_sec = test_duration_sec.strip("S")
        except:
            logger.debug("no S on duration time")
            
        test_duration_ms = long(test_duration_sec) * 1000
        start_time = test_time_ms - test_duration_ms
    
        file_name = os.path.basename(self.csv_file)
        importdoc["_source"]['ceph_benchmark_test']['common']['test_info']['file'] = file_name 
        
        thread_n_metric = file_name.split('.')[1]
        thread, metric_name = thread_n_metric.split('_', 1)
        
        tmp_doc = {
            'fio': {
                'fio_logs': {
                    metric_name: {}
                    }
                }
            }
        
        with open(self.csv_file) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in (readCSV):

                ms = float(row[0]) + float(start_time)
                newtime = datetime.datetime.fromtimestamp(ms / 1000.0)
                importdoc["_source"]['date'] = newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                
                tmp_doc['fio']['fio_logs'][metric_name]['metic_value'] = int(row[1])
                tmp_doc['fio']['fio_logs']['data direction'] = row[2]
                tmp_doc['fio']['fio_logs']['fio_thread'] = thread
                  
                #importdoc["_source"]["test_data"][metric_name] = int(row[1])
                #importdoc["_source"]["test_data"]['data direction'] = row[2]
                #importdoc['_source']['test_data']['fio_thread'] = thread 
                
                importdoc["_source"]['ceph_benchmark_test']["test_data"] = tmp_doc
                importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                yield importdoc  # XXX: TODO change to yield a
                
                
                