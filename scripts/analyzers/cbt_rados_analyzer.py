import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, itertools
from scribes import *
from . import cbt_pbench_analyzer
from datetime import timedelta
from ansible.modules.system import hostname

logger = logging.getLogger("index_cbt")

def analyze_cbt_rados_results(tdir, cbt_config_obj, test_metadata):

    logger.info("Processing Rados benchmark results.")
    
    metadata = {}
    metadata = test_metadata
    rados_json_results_transcriber_generator = cbt_rados_scribe.rados_json_results_transcriber(metadata)
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if 'benchmark_config.yaml' in fname:
                benchmark_data = yaml.load(open(fname))
                metadata['ceph_benchmark_test']['test_config'] = benchmark_data['cluster']
                logger.debug(json.dumps(metadata, indent=1))
                
                if metadata['ceph_benchmark_test']['test_config']['op_size']: metadata['ceph_benchmark_test']['test_config']['op_size'] = int(metadata['ceph_benchmark_test']['test_config']['op_size']) / 1024
                
                if "radosbench" in metadata['ceph_benchmark_test']['test_config']['benchmark']:
                    
                    write_path = "%s/write" % dirpath
                    metadata['ceph_benchmark_test']['test_config']['mode'] = "write"
                    #analyze rados output files
                    
                    analyze_cbt_rados_files_generator = analyze_cbt_rados_files(write_path, rados_json_results_transcriber_generator, copy.deepcopy(metadata))
#                     for cbt_rados_obj in analyze_cbt_rados_files_generator:
#                         yield cbt_rados_obj
                    
                    #analyze rados wrtie pbench logs
#                     analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(write_path, cbt_config_obj, copy.deepcopy(metadata))
#                     for pbench_obj in analyze_cbt_Pbench_data_generator:
#                         yield pbench_obj
                    
                    if not metadata['ceph_benchmark_test']['test_config']['write_only']:
                        if "seq" in metadata['ceph_benchmark_test']['test_config']['readmode']:
                            read_path = "%s/seq" % dirpath
                            logger.debug(read_path)
                            metadata['ceph_benchmark_test']['test_config']['mode'] = "read"
                        elif "rand" in metadata['ceph_benchmark_test']['test_config']['readmode']:
                            read_path = "%s/rand" % dirpath
                            logger.debug(read_path)
                            metadata['ceph_benchmark_test']['test_config']['mode'] = "randread"
                        elif not metadata['ceph_benchmark_test']['test_config']['readmode']:
                            read_path = "%s/seq" % dirpath
                            logger.debug(read_path)
                            metadata['ceph_benchmark_test']['test_config']['mode'] = "read"
                        
                        analyze_cbt_rados_files_generator = analyze_cbt_rados_files(read_path, rados_json_results_transcriber_generator, copy.deepcopy(metadata))
#                         for cbt_rados_obj in analyze_cbt_rados_files_generator:
#                             yield cbt_rados_obj
                        
#                         analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(read_path, cbt_config_obj, copy.deepcopy(metadata))
#                         for pbench_obj in analyze_cbt_Pbench_data_generator:
#                             yield pbench_obj
                            
    for import_obj in rados_json_results_transcriber_generator.emit_rados_json_files():
        yield import_obj
        
    yield rados_json_results_transcriber_generator
                            
def analyze_cbt_rados_files(tdir, json_results_scribe, metadata):
    logger.info("Processing rados json files...")
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
#             if "output" in fname and "json" not in fname:
                #get raw output file and seperated json file and pass them to a transcriber object
#                 rados_transcriber_obj = cbt_rados_scribe.rados_transcriber(fname, copy.deepcopy(metadata))
#                 yield rados_transcriber_obj
            if "json_output" in fname:
                json_results_scribe.add_json_file(fname, copy.deepcopy(metadata))
                          
                
     