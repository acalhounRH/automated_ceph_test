import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, itertools
from scribes import *
from . import cbt_pbench_analyzer
from datetime import timedelta


logger = logging.getLogger("index_cbt")

def analyze_cbt_smallfile_results(tdir, cbt_config_obj, test_metadata):
    
    logger.info("Processing Rados benchmark results.")
    metadata = {}
    metadata = test_metadata
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if 'benchmark_config.yaml' in fname:
                benchmark_data = yaml.load(open(fname))
                metadata['ceph_benchmark_test']['test_config'] = benchmark_data['cluster']
                logger.debug(json.dumps(metadata, indent=1))
                
                if "smallfile" in metadata['ceph_benchmark_test']['test_config']['benchmark']:
                    
                    smallfile_transcriber_obj_generator = cbt_smallfile_scribe.smallfile_transcriber(dirpath, "smfresult.json", copy.deepcopy(metadata))
                    yield smallfile_transcriber_obj_generator 
                    
                    analyze_cbt_Pbench_data_generator = cbt_pbench_analyzer.analyze_cbt_Pbench_data(write_path, cbt_config_obj, copy.deepcopy(metadata))
                    for pbench_obj in analyze_cbt_Pbench_data_generator:
                        yield pbench_obj