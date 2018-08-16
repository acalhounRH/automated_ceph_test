#! /usr/bin/python

import os, sys, json, time, types, csv, copy
import logging
import datetime
from time import gmtime, strftime
from datetime import timedelta
from elasticsearch import Elasticsearch, helpers
import threading
from threading import Thread
from collections import deque
import multiprocessing
import getopt

def es_index(es, a):

    actions = copy.deepcopy(a)
    index = True
    while index:
        try:
            bulk_status = int((es.cat.thread_pool(thread_pool_patterns='write', format=json)).split(" ")[3])
            wait_counter=1
            #logging.info("waiting for available bulk thread...")

            while bulk_status > 25:
                wait_time = 10 * wait_counter
                logging.warn("bulk thread pool high(%s), throttling for %s seconds" % (bulk_status, wait_time))
                time.sleep(wait_time)

                if wait_counter == 4:
                    wait_counter = 1
                else:
                    wait_counter += 1

                bulk_status = int((es.cat.thread_pool(thread_pool_patterns='write', format=json)).split(" ")[3])

            logging.info('Bulk indexing')
            deque(helpers.parallel_bulk(es, actions, chunk_size=1000, thread_count=1, request_timeout=60), maxlen=0)
            #logging.info("indexing complete...")
            index = False
        except Exception as e:
            bulk_status = (es.cat.thread_pool(thread_pool_patterns='write', format=json)).split(" ")[3]
            error_doc = {}
            error_status_ary = []
            error_doc = e.args
            error_type = type(e)
            try:
                for i in error_doc:
                    if isinstance(i, list):
                        for j in i:
                            if j['index']['status'] not in error_status_ary:
                                error_status_ary.append(j['index']['status'])
                for i in error_status_ary:
                        logging.error("Failed to index - Status: %s - %s" % (i, type(e)))
            except:
                logging.error("Failed to index")

