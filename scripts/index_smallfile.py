#! /usr/bin/python

#This script should be used for indexing small file results

import getopt

from proto_py_es_bulk import *
from scribes import *
from utils.common_logging import setup_loggers

logger = logging.getLogger("index_cosbench")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    es, test_id, test_mode = argument_handler()
    
    if test_mode:
        for i in process_data_generator(test_id, workload_list):
            logger.debug(json.dumps(i, indent=4))
    else:
        try:
            res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, process_data_generator(test_id))
                 
            FMT = '%Y-%m-%dT%H:%M:%SGMT'
            start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
            end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
                 
            start_t = datetime.datetime.strptime(start_t, FMT)
            end_t = datetime.datetime.strptime(end_t, FMT)
            tdelta = end_t - start_t
            logger.info("Duration of indexing - %s" % tdelta)
            logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry))
        except e as exception:
            logger.error(e.message) 
            sys.exit(1)
    
    
def process_data_generator(test_id,):
    
    object_generator = process_data(test_id, workload_list)
    
    for obj in object_generator:
        for action in obj.emit_actions():
            yield action
            
def process_data(test_id):
    
    ###########################################################################
    ###########################################################################
    #UPDATE TO YIELD SMALLFILE SCRIBE OBJECT(S)
    print "UPDATE TO YIELD SMALLFILE SCRIBE OBJECT"
    #parse archive directory
    #if smallfile data file found 
        #smallfile_scribe_generator = smallfile_scribe.smallfile_transcriber(test_id)
        #yield smallfile_scribe_generator
    ###########################################################################
    ###########################################################################
    
    
def argument_handler():
    log_level = logging.INFO   
    test_id = ""
    host = ""
    port = ""
    test_mode = False
    output_file=None

    usage = """ 
            Usage:
                evaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>
                
                -t or --test_id - test identifier
                -h or --host - Elasticsearch host ip or hostname
                -p or --port - Elasticsearch port (elasticsearch default is 9200)
                -w or --workloads - a list of workloads that should be imported 
            """
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 't:h:p:w:o:d', ['test_id=', 'host=', 'port=', 'workloads', 'debug', 'output_file' , 'test_mode'])
    except getopt.GetoptError:
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-t', '--test_id'):
            test_id = arg
        if opt in ('-h', '--host'):
            host = arg
        if opt in ('-p', '--port'):
            esport = arg
        if opt in ('--test_mode'):
            test_mode = True
        if opt in ('-o', '--output_file'):
            output_file = arg
        if opt in ('-d', '--debug'):
            log_level = logging.DEBUG

        
    setup_loggers("index_cosbench", log_level, output_file)

    if host and test_id and esport:
        logger.info("Test ID: %s, Host: %s, Port: %s " % (test_id, host, esport))
    else:
        logger.info(usage)
        exit (1)

    es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        ) 

    return es, test_id, workload_list, test_mode


if __name__ == '__main__':
    main()
    
