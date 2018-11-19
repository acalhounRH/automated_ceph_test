#! /usr/bin/python

import multiprocessing
import logging
from utils.common_logging import setup_loggers

logger = logging.getLogger("multiprocess_example")
setup_loggers("multiprocess_example", logging.DEBUG) 

_max_subprocesses = multiprocessing.cpu_count() / 2

def main():
    logger.info("STARTING THE EXAMPLE TEST")
    
    pool = multiprocessing.Pool(processes = _max_subprocesses)
    test_list = test_list_generator()
    my_sample = sample()
    for i in test_list:
        pool.apply_async(f, args=(i,my_sample,))
    pool.close()
    pool.join()
     

def test_list_generator():
    
    test_list = []
    for i in xrange(0, 10):
        test_list.append(i)
        
    return test_list

def f(name, obj):
    logger.debug('hello %s %s' % (name, obj.word))
    
class sample():
    def __init__(self):
        self.word = "THIS"
    
if __name__ == '__main__':
    main()
    