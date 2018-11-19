import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket
from scribes import *
import cbt_pbench_analyzer

logger = logging.getLogger("index_cbt")

class analyze_cbt_fio_results():
    
    def __init__(self, tdir, cbt_config_obj, test_metadata, type):
        self.target_dir = tdir
        self.cbt_config = cbt_config_obj
        self.metadata = test_metadata
        self.analysis_type = type

    
    def emit_scribes(self):
        #Will emit scribe obejcts for each particular file found. 
        logger.info("Processing RBD fio benchmark results.")
        test_id = self.metadata['ceph_benchmark_test']['common']['test_info']['test_id']
        
        metadata = {}
        metadata = self.metadata          
        if "benchmark" in self.analysis_type:            
            analyze_cbt_fiologs_generator = self.analyze_cbt_fiologs(self.target_dir, self.cbt_config, copy.deepcopy(self.metadata))
            for fiolog_transcriber_generator_obj in analyze_cbt_fiologs_generator:
                yield fiolog_transcriber_generator_obj
                                      
            #process pbench logs
            analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(self.target_dir, self.cbt_config, copy.deepcopy(self.metadata))
            for pbench_transcriber_obj in analyze_cbt_Pbench_data_generator:
                yield pbench_transcriber_obj
        
        if "archive" in self.analysis_type:
            logger.info("Processing fio json files...")
            fiojson_results_transcriber_generator = cbt_fiojson_scribe.fiojson_results_transcriber(copy.deepcopy(self.metadata))
            previous_dir = ""
            for dirpath, dirs, files in os.walk(self.target_dir):
                for filename in files:
                    if "json_" in filename:
                        if previous_dir is not dirpath:
                            test_config = yaml.load(open("%s/benchmark_config.yaml" % dirpath))
                            self.metadata['ceph_benchmark_test']['test_config'] = test_config["cluster"]
                            previous_dir = dirpath
                        json_file = os.path.join(dirpath,filename)
                        if os.path.getsize(json_file) > 0: 
                            fiojson_results_transcriber_generator.add_json_file(json_file, copy.deepcopy(self.metadata))
                        else:
                            logger.warn("Found corrupted JSON file, %s." % json_file)
                                           
            for fiojson_file_transcriber in fiojson_results_transcriber_generator.get_fiojson_importers():
                yield fiojson_file_transcriber
                
            yield fiojson_results_transcriber_generator
    
    
    def listdir_fullpath(self, d):
        return [os.path.join(d, f) for f in os.listdir(d)]
    
    
    def analyze_cbt_fiologs(self, tdir, cbt_config_obj, test_metadata):
    
        logger.info("Processing fio logs...")
        test_files = sorted(self.listdir_fullpath(tdir), key=os.path.getctime)
    
        for file in test_files:
            if ("_iops" in file) or ("_lat" in file):
            #if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):
                metadata = test_metadata
                jsonfile = "%s/json_%s.%s" % (tdir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
                hostname = os.path.basename(file).split('log.', 1)[1]
                
                metadata['ceph_benchmark_test']['common']['hardware']['hostname'] = hostname
                try:
                    metadata['ceph_benchmark_test']['application_config']['ceph_config']['ceph_node-type'] = cbt_config_obj.get_host_type(hostname)
                except:
                    logger.debug("Unable to get host type list")
    
                fiolog_transcriber_generator = cbt_fiolog_scribe.fiolog_transcriber(file, jsonfile, metadata)
                yield fiolog_transcriber_generator
            
            