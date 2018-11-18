#! /usr/bin/python

import multiprocessing
import logging
from utils.common_logging import setup_loggers

logger = logging.getLogger("multiprocess_example")
setup_loggers("multiprocess_example", logging.DEBUG) 

_max_subprocesses = multiprocessing.cpu_count() / 2

def main():
    logger.info("STARTING THE EXAMPLE TEST")
    
    test_list = [1,2,3,4,5,6,7,8,9]
    
    pool = multiprocessing.Pool(processes = _max_subprocesses)
    for i in test_list_generator:
        pool.apply_async(f, args=(i,))
    pool.close()
    pool.join()
     

def test_list_generator():
    for i in xrange(0, 10):
        return i

def f(name):
    logger.debug('hello %s' % name)
    

if __name__ == '__main__':
    main()
    