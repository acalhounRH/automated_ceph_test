#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket, getopt
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
from proto_py_es_bulk import *
from scribes import *
from util.common_logging import setup_loggers

logger = logging.getLogger("index_cbt")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    #logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    test_id = ""
    host = ""
    port = ""
    log_level = logging.INFO
    usage = """ 
            Usage:
                evaluatecosbench_pushes.py -t <test id> -h <host> -p <port>
                
                -t or --test_id - test identifier
                -h or --host - Elasticsearch host ip or hostname
                -p or --port - Elasticsearch port (elasticsearch default is 9200)
                -l or --log_level 0 - debug, 1 - info, 2 - warning, 3 - error, 4 - critical
            """
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 't:h:p:d', ['test_id=', 'host=', 'port=', 'debug'])
    except getopt.GetoptError:
        print usage 
        exit(1)

    for opt, arg in opts:
        if opt in ('-t', '--test_id'):
            test_id = arg
        if opt in ('-h', '--host'):
            host = arg
        if opt in ('-p', '--port'):
            esport = arg
        if opt in ('-d', '--debug'):
            log_level = logging.DEBUG
                       
    setup_loggers(log_level)    
    
    if host and test_id and esport:
        logger.info("Test ID: %s, Elasticsearch host and port: %s:%s " % (test_id, host, esport))
    else:
        logger.error(usage)
#        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
        exit ()

    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        ) 

    ###: TODO need to add test mode and turn this on and the real streaming bulk call off. 
#     for i in process_data_generator(test_id):
#         print json.dumps(i, indent=1)
  
    res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, process_data_generator(test_id))
     
    FMT = '%Y-%m-%dT%H:%M:%SGMT'
    start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
    end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
     
    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)
    tdelta = end_t - start_t
    logger.info("Duration of indexing - %s" % tdelta)
    logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 


#########################################################################

def process_data_generator(test_id):
    
    object_generator = process_data(test_id)

    for obj in object_generator:
        for action in obj.emit_actions():
            yield action

def process_data(test_id):
    test_metadata = {}
    test_metadata['ceph_benchmark_test'] = {
        "application_config": {
            "ceph_config": {}
            },
        "common": {
            "hardware": {},
            "test_info": {}
            },
        "test_config": {}
        }
    test_metadata['ceph_benchmark_test']['common']['test_info']['test_id'] = test_id
    
    #parse CBT achive dir and call process method
    for dirpath, dirs, files in os.walk("."):
        for filename in files:
            fname = os.path.join(dirpath,filename)
            #capture cbt configuration 
            if 'cbt_config.yaml' in fname:
                logger.info("Gathering CBT configuration settings...")
                cbt_config_gen = cbt_config_scribe.cbt_config_transcriber(test_id, fname)             
                yield cbt_config_gen
            
                #if rbd test, process json data 
                if "librbdfio" in cbt_config_gen.config['benchmarks']:
                    process_CBT_fio_results_generator = process_CBT_fio_results(dirpath, cbt_config_gen, copy.deepcopy(test_metadata))
                    for fiojson_obj in process_CBT_fio_results_generator:
                        yield fiojson_obj
                #if radons bench test, process data
                 
                if "radosbench" in cbt_config_gen.config['benchmarks']:
                    logger.warn("rados bench is under development")
                    process_CBT_rados_results_generator = process_CBT_rados_results(dirpath, cbt_config_gen, copy.deepcopy(test_metadata))
                    for rados_obj in process_CBT_rados_results_generator:
                        yield rados_obj
  
def process_CBT_fio_results(tdir, cbt_config_obj, test_metadata):
    
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
                
                if op_size_bytes: 
                     op_size_kb = int(op_size_bytes) / 1024
                     metadata['ceph_benchmark_test']['test_config']['op_size'] = op_size_kb
                
                if "librbdfio" in metadata['ceph_benchmark_test']['test_config']['benchmark']:
                    #process fio logs
                    process_CBT_fiologs_generator = process_CBT_fiologs(dirpath, cbt_config_obj, copy.deepcopy(metadata))
                    for fiolog_obj in process_CBT_fiologs_generator:
                        yield fiolog_obj
                
                    test_files = sorted(listdir_fullpath(dirpath), key=os.path.getctime) # get all samples from current test dir in time order
                    logger.info("Processing fio json files...")
                    for json_file in test_files:
                        if "json_" in json_file:
                            if os.path.getsize(json_file) > 0: 
                                fiojson_results_transcriber_generator.add_json_file(json_file, copy.deepcopy(metadata))
                            else:
                                logger.warn("Found corrupted JSON file, %s." % json_file)
                                
                    #process pbench logs
                    process_CBT_Pbench_data_generator = process_CBT_Pbench_data(dirpath, cbt_config_obj, copy.deepcopy(metadata))
                    for pbench_obj in process_CBT_Pbench_data_generator:
                        yield pbench_obj
                            
                
    for import_obj in fiojson_results_transcriber_generator.get_fiojson_importers():
        yield import_obj
        
    yield fiojson_results_transcriber_generator

def process_CBT_rados_results(tdir, cbt_config_obj, test_metadata):

    logger.info("Processing Rados benchmark results.")
    
    metadata = {}
    metadata = test_metadata
    for dirpath, dirs, files in os.walk(tdir):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if 'benchmark_config.yaml' in fname:
                for line in open(fname, 'r'):
                    benchmark_data = yaml.load(open(fname))
                    metadata['ceph_benchmark_test']['test_config'] = benchmark_data['cluster']
                
                if metadata['ceph_benchmark_test']['test_config']['op_size']: metadata['ceph_benchmark_test']['test_config']['op_size'] = int(metadata['ceph_benchmark_test']['test_config']['op_size']) / 1024
                
                if "radosbench" in metadata['ceph_benchmark_test']['test_config']['benchmark']:
                    
                    #process pbench logs
#                     write_path = "%s/write" % dirpath
#                     metadata['ceph_benchmark_test']['test_config']['mode'] = "write"
#                     process_CBT_Pbench_data_generator = process_CBT_Pbench_data(write_path, cbt_config_obj, copy.deepcopy(metadata))
#                     for pbench_obj in process_CBT_Pbench_data_generator:
#                         yield pbench_obj
                    
                    if not metadata['ceph_benchmark_test']['test_config']['write_only']:
                        read_path = "%s/seq" % dirpath
                        metadata['ceph_benchmark_test']['test_config']['mode'] = "read"
                        process_CBT_Pbench_data_generator = process_CBT_Pbench_data(read_path, cbt_config_obj, copy.deepcopy(metadata))
                        for pbench_obj in process_CBT_Pbench_data_generator:
                            yield pbench_obj           
  
def process_CBT_Pbench_data(tdir, cbt_config_obj, test_metadata):

    logger.info("Processing pbench data...")
    #For each host in tools default create pbench scribe object for each csv file
    hosts_dir = "%s/tools-default" % tdir
        
    for host in os.listdir(hosts_dir):
        host_dir_fullpath = "%s/%s" % (hosts_dir, host) 
        if os.path.isdir(host_dir_fullpath):
            for pdirpath, pdirs, pfiles in os.walk(host_dir_fullpath.strip()):
                for pfilename in pfiles:
                    pfname = os.path.join(pdirpath, pfilename)
                    #for ever tool collect csvs and...  tool name, tool dir and metadata 
                    if ".csv" in pfname:
                        metadata = {}
                        metadata = test_metadata
                        
                        hostname = host
                        tool = pfname.split("/")[-2]
                        metadata['ceph_benchmark_test']['common']['hardware']['hostname'] = hostname
                        metadata['ceph_benchmark_test']['common']['hardware']['ipaddress'] = socket.gethostbyname(hostname)
                        metadata['ceph_benchmark_test']['application_config']['ceph_config']['ceph_node_type'] = cbt_config_obj.get_host_type(hostname)
                        metadata['ceph_benchmark_test']['common']['test_info']['tool'] = tool
                        logger.debug(tool)
                        metadata['ceph_benchmark_test']['common']['test_info']['file_name'] = os.path.basename(pfname)
                    
                        pb_transcriber_generator = cbt_pbench_scribe.pbench_transcriber(pfname, metadata)
                        yield pb_transcriber_generator
        else:
            logger.warn("Pbench directory not Found, %s does not exist." % host_dir_fullpath)

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def process_CBT_fiologs(tdir, cbt_config_obj, test_metadata):

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
            metadata['ceph_benchmark_test']['application_config']['ceph_config']['ceph_node-type'] = cbt_config_obj.get_host_type(hostname)
            

            fiolog_transcriber_generator = cbt_fiolog_scribe.fiolog_transcriber(file, jsonfile, metadata)
            yield fiolog_transcriber_generator

###############################CLASS DEF##################################
     
 
if __name__ == '__main__':
    main()





