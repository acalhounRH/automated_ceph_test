
import yaml, os, time, json, hashlib
import socket, datetime, statistics, logging
from collections import defaultdict

logger = logging.getLogger("index_cbt")

class fiojson_file_transcriber:

    def __init__(self, json_file, metadata):
        self.metadata = metadata
        self.json_file = json_file
        
    def emit_actions(self):
        importdoc = {}
        importdoc["_index"] = "cbt_librbdfio-json-indextest1"
        importdoc["_type"] = "librbdfiojsondata"
        importdoc["_op_type"] = "create"
        importdoc['_source'] = self.metadata

        logger.debug("Indexing %s" % self.json_file)
        tmp_doc = {
            "fio": {
                "fio_json": {
                    }
                  }
            }
        
        json_doc = json.load(open(self.json_file))
        #create header dict based on top level objects
        importdoc['_source']['date'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.localtime(json_doc['timestamp']))
        
        tmp_doc['fio']['fio_json']['global_options'] = json_doc['global options']
        tmp_doc['fio']['fio_json']['global_options']['bs'] = ( int(tmp_doc['fio']['fio_json']['global_options']['bs'].strip('B')) / 1024)
        tmp_doc['fio']['fio_json']['timestamp_ms'] = json_doc['timestamp_ms']
        tmp_doc['fio']['fio_json']['timestamp'] = json_doc['timestamp']
        tmp_doc['fio']['fio_json']['fio_version'] = json_doc['fio version']
        tmp_doc['fio']['fio_json']['time'] = json_doc['time']

        
        
        for job in json_doc['jobs']:
            tmp_doc['fio']['fio_json']['job'] = job
            #XXX: TODO need to add total_iops for all jons in current record
            tmp_doc['fio']['fio_json']['total_iops'] = int(tmp_doc['fio']['fio_json']['job']['write']['iops']) + int(tmp_doc['fio']['fio_json']['job']['read']['iops'])
            
            importdoc['_source']['ceph_benchmark_test']['test_data'] = tmp_doc
            importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
            yield importdoc
            
class fiojson_results_transcriber:
    
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
        json_data['metadata'] = metadata 
        self.json_data_list.append(json_data)
        
    def calculate_iops_sum(self):
        
        for cjson_data in self.json_data_list:
            iteration = cjson_data['metadata']['ceph_benchmark_test']['test_config']['iteration']
            op_size = cjson_data['metadata']['ceph_benchmark_test']['test_config']['op_size']
            mode = cjson_data['metadata']['ceph_benchmark_test']['test_config']['mode']
            
            if iteration not in self.iteration_list: self.iteration_list.append(iteration) 
            if mode not in self.operation_list: self.operation_list.append(mode)
            if op_size not in self.block_size_list: self.block_size_list.append(op_size)
             
        for iteration in self.iteration_list:
            self.sumdoc[iteration] = {}
            for mode in self.operation_list:
                self.sumdoc[iteration][mode] = {}
                for op_size in self.block_size_list:
                    self.sumdoc[iteration][mode][op_size] = {}
            
            #get measurements
        for json_data in self.json_data_list:
            json_doc = json.load(open(json_data['jfile']))
            
            iteration = json_data['metadata']['ceph_benchmark_test']['test_config']['iteration']
            op_size = json_data['metadata']['ceph_benchmark_test']['test_config']['op_size']
            mode = json_data['metadata']['ceph_benchmark_test']['test_config']['mode']
            
            if not self.sumdoc[iteration][mode][op_size]:
                self.sumdoc[iteration][mode][op_size]['date'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.localtime(json_doc['timestamp']))
                self.sumdoc[iteration][mode][op_size]['write'] = 0
                self.sumdoc[iteration][mode][op_size]['read'] = 0
            
            for job in json_doc['jobs']:      
                self.sumdoc[iteration][mode][op_size]['write'] += int(job["write"]["iops"])
                self.sumdoc[iteration][mode][op_size]['read'] += int(job["read"]["iops"])
        
    def get_fiojson_importers(self):
        
        for json_file in self.json_data_list: 
            #json_metadata = {}
            json_metadata = json_file['metadata']
            fiojson_import_generator = fiojson_file_transcriber(json_file['jfile'], json_metadata)
            yield fiojson_import_generator
            
    def emit_actions(self):
        
        importdoc = {}
        importdoc["_index"] = "cbt_librbdfio-summary-indextest1-fixed"
        importdoc["_type"] = "librbdfiosummarydata"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.metadata
        
        tmp_doc = {}
        
        self.calculate_iops_sum()
        
        for oper in self.operation_list:
            for obj_size in self.block_size_list:
                waver_ary = []
                raver_ary = []
                total_ary = []
                tmp_doc = {}
                tmp_doc['object_size'] = obj_size # set document's object size
                tmp_doc['operation'] = oper # set documents operation
                firstrecord = True
                calcuate_percent_std_dev = False
                for itera in self.iteration_list: # 
                    waver_ary.append(self.sumdoc[itera][oper][obj_size]['write'])
                    raver_ary.append(self.sumdoc[itera][oper][obj_size]['read'])
    
                    if firstrecord:
                        importdoc["_source"]['date'] = self.sumdoc[itera][oper][obj_size]['date']
                        firstrecord = True

                read_average = (sum(raver_ary)/len(raver_ary))
                if read_average > 0.0:
                    tmp_doc['read-iops'] = read_average
                    if len(raver_ary) > 1:
                        calcuate_percent_std_dev = True
                else:
                    tmp_doc['read-iops'] = 0
        
                write_average = (sum(waver_ary)/len(waver_ary))
                if write_average > 0.0:
                    tmp_doc['write-iops'] = write_average
                    if len(waver_ary) > 1:
                        calcuate_percent_std_dev = True 
                else:
                    tmp_doc['write-iops'] = 0
        
                tmp_doc['total-iops'] = (tmp_doc['write-iops'] + tmp_doc['read-iops'])
                
                if calcuate_percent_std_dev:
                    if "read" in oper:
                        tmp_doc['std-dev-%s' % obj_size] = round(((statistics.stdev(raver_ary) / read_average) * 100), 3)
                    elif "write" in oper: 
                        tmp_doc['std-dev-%s' % obj_size] = round(((statistics.stdev(waver_ary) / write_average) * 100), 3)
                    elif "randrw" in oper:
                        tmp_doc['std-dev-%s' % obj_size] = round((((statistics.stdev(raver_ary) + statistics.stdev(waver_ary)) / tmp_doc['total-iops'])* 100), 3)
                
                importdoc["_source"]['ceph_benchmark_test']['test_data'] = tmp_doc
                importdoc["_id"] = hashlib.md5(str(importdoc).encode()).hexdigest()
                yield importdoc   