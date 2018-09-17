import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, itertools
from scribes import *
import cbt_pbench_analyzer

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
                with open(fname) as f:
                    time_set = False
                    line_count = 0
                    result = itertools.islice(f, 4, None)
                    for i in result:
                        if line_count <=19:
                            print i 
                            line_count += 1
                        else:
                            line_count = 0 
                            if not time_set:
                                print "set_time"
                                time_set = True
                            else:
                                print "skipping the line, time set" 
#                 line_count = 0
#                 for line in open(fname, 'r'):
#                     if line_count > 5:
#                         
#                     print line
#                     line_count += 1
                    
                
     