import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, itertools
from scribes import *
import cbt_pbench_analyzer
from datetime import timedelta

logger = logging.getLogger("index_cbt")

def analyze_cbt_rados_results(tdir, cbt_config_obj, test_metadata):

    logger.info("Processing Rados benchmark results.")
    
    metadata = {}
    metadata = test_metadata
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if 'benchmark_config.yaml' in fname:
                benchmark_data = yaml.load(open(fname))
                metadata['ceph_benchmark_test']['test_config'] = benchmark_data['cluster']
                
                if metadata['ceph_benchmark_test']['test_config']['op_size']: metadata['ceph_benchmark_test']['test_config']['op_size'] = int(metadata['ceph_benchmark_test']['test_config']['op_size']) / 1024
                
                if "radosbench" in metadata['ceph_benchmark_test']['test_config']['benchmark']:
                    
                    write_path = "%s/write" % dirpath
                    metadata['ceph_benchmark_test']['test_config']['mode'] = "write"
                    #analyze rados output files
                    
                    analyze_cbt_rados_json_files(write_path, cbt_config_obj, copy.deepcopy(metadata))
                    
                    #analyze rados wrtie pbench logs
                    analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(write_path, cbt_config_obj, copy.deepcopy(metadata))
                    for pbench_obj in analyze_cbt_Pbench_data_generator:
                        yield pbench_obj
                    
                    if not metadata['ceph_benchmark_test']['test_config']['write_only']:
                        read_path = "%s/seq" % dirpath
                        metadata['ceph_benchmark_test']['test_config']['mode'] = "read"
                        analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(read_path, cbt_config_obj, copy.deepcopy(metadata))
                        for pbench_obj in analyze_cbt_Pbench_data_generator:
                            yield pbench_obj
                            
def analyze_cbt_rados_json_files(tdir, cbt_config_obj, metadata):
    logger.info("Processing rados json files...")
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if "output" in fname and "json" not in fname:
                #get raw output file and seperated json file and pass them to a transcriber object
                with open(fname) as f:
                    header_list = ["Seconds since start", "current Operations", "started", "finished", "avg MB/s",  "cur MB/s", "last lat(s)",  "avg lat(s)"] 
                    time_set = False
                    placeholder_list = []
                    line_count = 0
                    result = itertools.islice(f, 4, None)
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
                                    
#                             if time_set:
#                                 #set time
#                                 time = start_time + tmp_doc["Seconds since start"]
#                             else:
#                                 #save record in list for postprocess after time has been found.
#                                 placeholder.append(tmp_doc)          
                            
                            #print json.dumps(tmp_doc, indent=1)
                            print i  
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
                                print sometime
                                print start_time
                                time_set = True 
                    
                
     