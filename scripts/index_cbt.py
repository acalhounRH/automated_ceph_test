#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging
import datetime
from time import gmtime, strftime
from elasticsearch import Elasticsearch, helpers
import threading
from threading import Thread
from collections import deque
import multiprocessing
from evaluators.fiojsonevaluator.py import fiojsonevaluator
from fiologevaluator.py import fiologevaluator
from pbenchevaluator.py import pbenchevaluator

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(process)d %(threadName)s: %(levelname)s - %(message)s ')
    
    #check for test id, if not, set generic test id
    if len(sys.argv) > 3:
        maindoc["_source"]['test_id'] = sys.argv[1]
        host = sys.argv[2]
        esport = sys.argv[3]
    else: 
        maindoc["_source"]['test_id'] = "librbdfio-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())

    globals()['es'] = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        ) 


    for i in process_data_generator():
        print json.dumps(i, indent=1)

#    es_index(es, process_data_generator())


##############################################################

def process_data_generator():
    
    object_generator = process_data()

    for obj in object_generator:
        for actions in obj.emit_actions():
            yield action

def process_data():
    test_metadata = {}
    test_metadata["_source"] = {}

    #XXX: TODO remove this?
    #if the pbench index doesnt exist create index
    if not es.indices.exists("pbench"):
        request_body = {"settings" : {"refresh_interval": "10s", "number_of_replicas": 0}}
        res = es.indices.create(index="pbench", body=request_body)
        logging.debug("response: '%s' " % (res))

    #parse CBT achive dir and call process method
    for dirpath, dirs, files in os.walk("."):
	for filename in files:
        	fname = os.path.join(dirpath,filename)
        	#for each benchmark capture benchmark metadata and process all data
        	if 'benchmark_config.yaml' in fname:
                    for line in open(fname, 'r'):
                	line = line.strip()
                        if 'mode:' in line:
                        	test_metadata['mode'] = line.split('mode:', 1)[-1]
                        elif 'op_size' in line:
                        	test_metadata['object_size'] = int(line.split('op_size:', 1)[-1]) / 1024
                        elif 'benchmark:' in line:
                        	test_metadata['benchmark'] = line.split('benchmark:', 1)[-1]
                    #XXX: TODO need to add iteration number to metadata
                    process_CBT_Pbench_data_generator = process_CBT_Pbench_data(test_directory, test_metadata)
                    for pbench_obj in process_CBT_Pbench_data_generator:
                        yield pbench_obj 
                    process_CBT_fiologs_generator = process_CBT_fiologs(test_directory, test_metadata)
                    for fiolog_obj in process_CBT_fiologs_generator:
                        yield fiolog_obj
                    process_CBT_fiojson_generator = process_CBT_fiojson(test_directory, test_metadata)
                    for fiojson_obj in process_CBT_fiojson_generator:
                        yield fiojson_obj


def process_CBT_Pbench_data(tdir, headerdoc):
    metadata = {}
    metadata["_index"] = "pbench"
    metadata["_type"] = "pbenchdata"
    metadata["_op_type"] = "create"

    #For each host in tools default create pbench scribe object for each csv file
    logging.info('processing data in benchmark %s, mode %s, object size %s' % (benchmarkdoc["_source"]['benchmark'], benchmarkdoc["_source"]['mode'], benchmarkdoc["_source"]['object_size']))
    hosts_dir = "%s/tools-default" % tdir
    for host in os.listdir(hosts_dir):
        host_dir_fullpath = "%s/%s" % (hosts_dir, host) 
    #def push_bulk_pbench_data_to_es(host_dir, headerdoc):
        for pdirpath, pdirs, pfiles in os.walk(host_dir_fullpath.strip()):
            for pfilename in pfiles:
                pfname = os.path.join(pdirpath, pfilename)
                if ".csv" in pfname:
                    
                    metadata["_source"] = headerdoc
                    metadata["_source"]['host'] = pfname.split("/")[5]
                    metadata["_source"]['tool'] = pfname.split("/")[6]
                    metadata["_source"]['file_name'] = pfname.split("/")[8]
                
                    pb_evaluator_generator = pbenchevaluator(csv, metadata)
                    yield pb_evaluator_generator

def process_CBT_fiojson(tdir, headerdoc):
    metadata = {}
    metadata["_index"] = "cbt_librbdfio-json-index"
    metadata["_type"] = "librbdfiojsondata"
    metadata["_op_type"] = "create"

    test_files = sorted(listdir_fullpath(dir), key=os.path.getctime) # get all samples from current test dir in time order
    for file in test_files:
        if "json_" in file:
#           (file, os.path.basename(cdir), averdoc['test_id'])
            fiojson_evaluator_generator = fiojsonevaluator(file, metadata)
            yield fiojson_evaluator_generator


def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def process_CBT_fiologs(tdir, headerdoc):
    metadata = {}
    metadata["_index"] = "cbt_librbdfio-log-index"
    metadata["_type"] = "librbdfiologdata"
    metadata["_op_type"] = "create"

        # get all samples from current test dir in time order
        test_files = sorted(listdir_fullpath(tdir), key=os.path.getctime)

        #for each fio log file capture test time in json file then yield evaluator object
        for file in test_files:
            if ("_iops" in file) or ("_lat" in file):
            #if ("_bw" in file) or ("_clat" in file) or ("_iops" in file) or ("_lat" in file) or ("_slat" in file):
                #fiologdoc = copy.deepcopy(headerdoc)
                metadata["_source"] = headerdoc
                jsonfile = "%s/json_%s.%s" % (tdir, os.path.basename(file).split('_', 1)[0], os.path.basename(file).split('log.', 1)[1])
                metadata["_source"]['host'] = os.path.basename(file).split('log.', 1)[1]
                
                fiolog_evaluator_generator = fiologevaluator(file, jsonfile, metadata)
                yield fiolog_evaluator_generator


if __name__ == '__main__':
    main()
