
import yaml, os, time, json, hashlib, sys
import socket, datetime, csv, logging


logger = logging.getLogger("index_cbt")

class pbench_transcriber:

    def __init__(self, csv_file, metadata, cbt_config_obj):
        self.csv_file = csv_file
        self.metadata = metadata
        
        host = self.metadata['ceph_benchmark_test']['common']['hardware']['hostname']
        self.host_info = cbt_config_obj.get_host_info(host)
        
    def get_service_id(self, service_pid):
        instance = -1
        for child in self.host_info['children']:
            if service_pid in child['service_pid']:
                instance = child['service_id']
        
        return instance

    def emit_actions(self):
        importdoc = {}
        importdoc["_index"] = "pbenchtest1"
        importdoc["_type"] = "pbenchdata"
        importdoc["_op_type"] = "create"
        importdoc['_source'] = self.metadata
        
        tool = importdoc['_source']['ceph_benchmark_test']['common']['test_info']['tool']         
        file_name = importdoc['_source']['ceph_benchmark_test']['common']['test_info']['file_name']
        file_name = file_name.split('.',1)[0]
        
        tmp_doc = {
            tool: {
                file_name: {}
                }
            }
        
        #logger.debug("Indexing %s" % self.csv_file)
        with open(self.csv_file) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            first_row = True
            col_ary = []
            
            for row in readCSV:
                if first_row:
                    col_num = len(row)
                    for col in range(col_num):
                        col_ary.append(row[col])
                        first_row = False
                else:
                    for col in range(col_num):
                        a = {}
                        
                        if 'timestamp_ms' in col_ary[col]:
                            ms = float(row[col])
                            thistime = datetime.datetime.fromtimestamp(ms / 1000.0)
                            importdoc['_source']['date'] = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        else:
                            try:
                                metric_value = float(row[col])
                            except Exception as e:
                                logger.error("Unable to convert %s to a float" % row[col])
                                logger.error("file %s " % self.csv_file)
                                logger.exception("Exception Triggered")
                                break
                                
                            if 'pidstat' in tool:
                                node_type_list = ["ceph-mon", "ceph-osd", "ceph-mgr", "ceph-mds", "ceph-rgw"]
                                pname = col_ary[col].split('/')[-1]
                                
                                for node_type in node_type_list:
                                    if  node_type in pname:    
                                        pid = col_ary[col].split('-', 1)[0]
                                        instance = self.get_service_id(pid)
                                        
                                        tmp_doc[tool][file_name]['process_name'] = node_type
                                        tmp_doc[tool][file_name]['service_id'] = instance
                                        tmp_doc[tool][file_name]['process_pid'] = pid
                                        
                                        if "cpu_usage" in file_name and self.host_info is not None:
                                            metric_value = metric_value / int(self.host_info['cpu_info']['CPU(s)'])

                                        tmp_doc[tool][file_name]['metric_value'] = metric_value
                                        a = importdoc
                            else:
                                tmp_doc[tool][file_name]['metric_stat'] = col_ary[col]
                                
                                if "cpuall" in file_name and self.host_info is not None:
                                    metric_value = metric_value / int(self.host_info['cpu_info']['CPU(s)'])
                                    
                                tmp_doc[tool][file_name]['metric_value'] = metric_value
                                a = importdoc
                        if a:
                                importdoc["_source"]['ceph_benchmark_test']["test_data"] = tmp_doc
                                importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
                                yield a
                    
                    