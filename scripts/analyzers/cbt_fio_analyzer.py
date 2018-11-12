import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket
from scribes import *
import cbt_pbench_analyzer

logger = logging.getLogger("index_cbt")

def analyze_cbt_fio_results(tdir, cbt_config_obj, test_metadata):
    
    logger.info("Processing RBD fio benchmark results.")
    test_id =  test_metadata['ceph_benchmark_test']['common']['test_info']['test_id']
    fiojson_results_transcriber_generator = cbt_fiojson_scribe.fiojson_results_transcriber(copy.deepcopy(test_metadata))
    metadata = {}
    metadata = test_metadata
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if 'benchmark_config.yaml' in fname:
                benchmark_data = yaml.load(open(fname))
                metadata['ceph_benchmark_test']['test_config'] = benchmark_data['cluster']
            
                
                op_size_bytes = metadata['ceph_benchmark_test']['test_config']['op_size']
                time_w_unit = metadata['ceph_benchmark_test']['test_config']['time']
                
                if op_size_bytes: 
                     op_size_kb = int(op_size_bytes) / 1024
                     metadata['ceph_benchmark_test']['test_config']['op_size'] = op_size_kb
                
                try:
                    if "S" in time_w_unit:  
                        time_wo_unit = time_w_unit.strip("S")
                        time_wo_unit = int(time_wo_unit)
                except:
                    time_wo_unit = time_w_unit
                    metadata['ceph_benchmark_test']['test_config']['time'] = time_wo_unit
                
                if "librbdfio" in metadata['ceph_benchmark_test']['test_config']['benchmark']:
                    #process fio logs
                    analyze_cbt_fiologs_generator = analyze_cbt_fiologs(dirpath, cbt_config_obj, copy.deepcopy(metadata))
                    for fiolog_obj in analyze_cbt_fiologs_generator:
                        yield fiolog_obj
                
                    test_files = sorted(listdir_fullpath(dirpath), key=os.path.getctime) # get all samples from current test dir in time order
                    logger.info("Processing fio json files...")
                    for json_file in test_files:
                        if "json_" in json_file:
                            if os.path.getsize(json_file) > 0: 
                                fiojson_results_transcriber_generator.add_json_file(json_file, copy.deepcopy(metadata))
                            else:
                                logger.warn("Found corrupted JSON file, %s." % json_file)
                                
#                     #process pbench logs
#                     analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(dirpath, cbt_config_obj, copy.deepcopy(metadata))
#                     for pbench_obj in analyze_cbt_Pbench_data_generator:
#                         yield pbench_obj
                            
                
    for import_obj in fiojson_results_transcriber_generator.get_fiojson_importers():
        yield import_obj
        
    yield fiojson_results_transcriber_generator
    
    
    
    
    
def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def analyze_cbt_fiologs(tdir, cbt_config_obj, test_metadata):

    logger.info("Processing fio logs...")
        # get all samples from current test dir in time order
    test_files = sorted(listdir_fullpath(tdir), key=os.path.getctime)

        #for each fio log file capture test time in json file then yield transcriber object
    for file in test_files:
    	if ("_iops" in file) or ("_lat" in file):
        #if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):
            metadata = {}
            #fiologdoc = copy.deepcopy(headerdoc)
            metadata = test_metadata
            jsonfile = "%s/json_%s.%s" % (tdir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
            hostname = os.path.basename(file).split('log.', 1)[1]
            
            metadata['ceph_benchmark_test']['common']['hardware']['hostname'] = hostname
            try:
                metadata['ceph_benchmark_test']['application_config']['ceph_config']['ceph_node-type'] = cbt_config_obj.get_host_type(hostname)
            except:
                logger.debug("Unable to set get host type list")

            fiolog_transcriber_generator = cbt_fiolog_scribe.fiolog_transcriber(file, jsonfile, metadata)
            yield fiolog_transcriber_generator
            
            