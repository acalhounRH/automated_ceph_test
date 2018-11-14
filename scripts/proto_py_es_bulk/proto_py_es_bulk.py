#! /usr/bin/python

import sys, os, time, json, errno, logging, math
from random import SystemRandom
from collections import deque, Counter
from elasticsearch import Elasticsearch, helpers
import time, logging, json

logger = logging.getLogger("index_cbt")

_request_timeout = 100000000*60
_MAX_SLEEP_TIME = 120
_op_type = "create"


def calc_backoff_sleep(backoff):
    global _r
    b = math.pow(2, backoff)
    return _r.uniform(0, min(b, ))

def tstos(ts=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S-%Z", time.gmtime(ts))
    

def streaming_bulk(es, actions):
    
    
    """
    streaming_bulk(es, actions, errorsfp)
     Arguments:
         es - An Elasticsearch client object already constructed
        actions - An iterable for the documents to be indexed
        errorsfp - A file pointer for where to write 400 errors
     Returns:
         A tuple with the start and end times, the # of successfully indexed,
        duplicate, and failed documents, along with number of times a bulk
        request was retried.
    """
     # These need to be defined before the closure below. These work because
    # a closure remembers the binding of a name to an object. If integer
    # objects were used, the name would be bound to that integer value only
    # so for the retries, incrementing the integer would change the outer
    # scope's view of the name.  By using a Counter object, the name to
    # object binding is maintained, but the object contents are changed.
    actions_deque = deque()
    actions_retry_deque = deque()
    retries_tracker = Counter()
    def actions_tracking_closure(cl_actions):
        ##get start_time
        logger.debug("WE ARE IN ACTIONS TRACKING CLOSUREs")
        start_time = time.time()
        ## actions counter = 0 
        actions_counter = 0
        len_diff = 0
        previous_length = 0
        object_list = []
        processing_duration_list = [] 
        for cl_action in cl_actions:
            assert '_id' in cl_action
            assert '_index' in cl_action
            assert '_type' in cl_action
            assert _op_type == cl_action['_op_type']
            new_length = len(actions_deque)
            len_diff = new_length - previous_length
            if len_diff < 0:
                stop_time = time.time()
                processing_duration = stop_time - start_time
                object_list.append(actions_counter)
                average_object_count = sum(object_list) / float(len(object_list))
                processing_duration_list.append(processing_duration)
                average_processing_duration = sum(processing_duration_list) / float(len(processing_duration_list))
                
                logger.debug("Response Returned - started at %s, finished at %s" % (time.ctime(int(start_time)), time.ctime(int(stop_time))))
                logger.debug("%s objects, with a processing duration of %s." % (actions_counter, processing_duration))
                logger.debug("Average object count %s, Average Processing Duration %s" % (average_object_count, average_processing_duration))
                start_time = time.time()
                actions_counter = 0
            
            actions_deque.append((0, cl_action))   # Append to the right side ...
            previous_length = len(actions_deque)
            ## number of actions que counter ++
            actions_counter += 1

            yield cl_action
        
            
            # if after yielding an action some actions appear on the retry deque
            # start yielding those actions until we drain the retry queue.
            backoff = 1
            while len(actions_retry_deque) > 0:
                time.sleep(calc_backoff_sleep(backoff))
                retries_tracker['retries'] += 1
                ## log ouput retries_tracker['retries']
                logger.debug(json.dumps(retries_tracker['retries'], indent=1))
                retry_actions = []
                # First drain the retry deque entirely so that we know when we
                # have cycled through the entire list to be retried.
                while len(actions_retry_deque) > 0:
                    retry_actions.append(actions_retry_deque.popleft())
                for retry_count, retry_action in retry_actions:
                    actions_deque.append((retry_count, retry_action))   # Append to the right side ...
                    yield retry_action
                # if after yielding all the actions to be retried, some show up
                # on the retry deque again, we extend our sleep backoff to avoid
                # pounding on the ES instance.
                backoff += 1
            
    beg, end = time.time(), None
    successes = 0
    duplicates = 0
    failures = 0
     # Create the generator that closes over the external generator, "actions"
     #, max_chunk_bytes=1048576
     #chunk_size=100000,  
    generator = actions_tracking_closure(actions)
    #streaming_bulk_generator = helpers.streaming_bulk(
    #setting max chunk bytes to 5MB documentations says try 5MB-15MB
    streaming_bulk_generator = helpers.parallel_bulk(
           es, generator,chunk_size=100000, max_chunk_bytes=5242880, raise_on_error=False,
           raise_on_exception=False, request_timeout=_request_timeout)

    for ok, resp_payload in streaming_bulk_generator:
       retry_count, action = actions_deque.popleft()
       try:
           resp = resp_payload[_op_type]
           status = resp['status']
       except KeyError as e:
           assert not ok
           # resp is not of expected form
           print(resp)
           status = 999
#        else:
#            assert action['_id'] == resp['_id']
       if ok:
           successes += 1
       else:
           if status == 409:
               if retry_count == 0:
                   # Only count duplicates if the retry count is 0 ...
                   #logger.debug("Duplicate record detected.")
                   #logger.debug(json.dumps(action, indent=1))
                   duplicates += 1
               else:
                   # ... otherwise consider it successful.
                   successes += 1
           elif status == 400:
               doc = {
                        "action": action,
                        "ok": ok,
                        "resp": resp,
                        "retry_count": retry_count,
                        "timestamp": tstos(time.time())
                        }
               jsonstr = json.dumps(doc, indent=4, sort_keys=True)
               logger.error(jsonstr)
#              errorsfp.flush()
               failures += 1
           else:
               # Retry all other errors
               print(resp)
               actions_retry_deque.append((retry_count + 1, action))
    end = time.time()
    assert len(actions_deque) == 0
    assert len(actions_retry_deque) == 0
    return (beg, end, successes, duplicates, failures, retries_tracker['retries'])
 