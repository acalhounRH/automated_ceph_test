from elasticsearch import Elasticsearch, helpers
from util.common_logging import setup_loggers
from proto_py_es_bulk import *
from hidapi.hidconsole import start_time



logger = logging.getLogger("index_cbt")

es_log = logging.getLogger("elasticsearch")
es_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib3")
urllib3_log.setLevel(logging.CRITICAL)

def main():
    print "start"
    #TODO instead of only supporting A:B comparisons, try using a comma seperated list in order to provide 1:* comparisons 
    es, comparison_id, test_id1, test_id2 = argument_handler()
    
    res_beg, res_end, res_suc, res_dup, res_fail, res_retry  = proto_py_es_bulk.streaming_bulk(es, process_data_generator(test_id))
      
    FMT = '%Y-%m-%dT%H:%M:%SGMT'
    start_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_beg))
    end_t = time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime(res_end))
      
    start_t = datetime.datetime.strptime(start_t, FMT)
    end_t = datetime.datetime.strptime(end_t, FMT)
    tdelta = end_t - start_t
    logger.info("Duration of indexing - %s" % tdelta)
    logger.info("Indexed results - %s success, %s duplicates, %s failures, with %s retries." % (res_suc, res_dup, res_fail, res_retry)) 
    

def test_data_generator(com_id. test_id_list,):
    object_generator = get_test_data(test_id)

    for obj in object_generator:
        for action in obj.emit_actions():
            #generate index name and id 
            #I.E add elasticsearch specific information to emitted data. 
            yield action
            
def get_test_data(comparison_id, test_id_list):
    
    get_start_time
    
    for test_id in test_id_list:
        obj = test_holder(test_id, comparison_id, start_time)
        yield obj 
    

class test_holder():
    def __init__(self):
        self.test_id
        self.comparison_id
        self.start_datetime_stamp
        self.offset
        
    def modify_time(self):
    
    def emit_actions(self, ):
        results = es.search(index="*test1", doc_type="fiologfile", size=10000,  body={"query": {"match": {"test_id.keyword": self.test_id}}})
        for doc in test1_results['hits']['hits']:
            print doc["_source"]['date'] 

def argument_handler():
    test_id = ""
    host = ""
    port = ""
    log_level = logging.INFO
    usage = """ 
            Usage:
                run2runcomparison.py -t <title> -t1 <test id 1>  -t <test id 2> -h <host> -p <port> 
                
                -t or --title - test identifier
                -t1 or --test-id1 - identifier for test A
                -t2 or --test-id2 - identifier for test B 
                -h or --host - Elasticsearch host ip or hostname
                -p or --port - Elasticsearch port (elasticsearch default is 9200)
                -d or --debug - enables debug (verbose) logging output
            """
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 't:t1:t2:h:p:d', ['title=', 'test-2=', 'test-1=', 'host=', 'port=', 'debug'])
    except getopt.GetoptError:
        print usage 
        exit(1)

    for opt, arg in opts:
        if opt in ('-t', '--title'):
            comparison_id = arg
        if opt in ('-t1', '--test-1'):
            test_id1 = arg
        if opt in ('-t2', '--test-2'):
            test_id2 = arg
        if opt in ('-h', '--host'):
            host = arg
        if opt in ('-p', '--port'):
            esport = arg
        if opt in ('-d', '--debug'):
            log_level = logging.DEBUG
                       
    setup_loggers(log_level)    
    
    if host and test_id and esport:
        logger.info("Comparison_id: %s - Comparing %s and %s." % (comparison_id, test_id1, test_id2))
        logger.info("Using Elasticsearch host and port: %s:%s " % (test_id, host, esport))
    else:
        logger.error(usage)
#        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
        exit ()

    es = Elasticsearch(
        [host],
        scheme="http",
        port=esport,
        )
    
    return es, comparison_id, test_id1, test_id2







if __name__ == '__main__':
    main()
