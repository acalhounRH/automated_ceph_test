#! /usr/bin/python

###:TODO THIS Needs to be converted into 
# evaluateMetaPerObj.py - script written by Ben England to 
# push results from rados_delete_create.sh script to elastic search
# modifying version of Alex Calhoun's similar scripting for fio

import os, sys, json, time, types, csv
from time import gmtime, strftime
import datetime
from elasticsearch import Elasticsearch
import numpy, scipy
from scipy import stats

es = Elasticsearch(
        ['10.18.81.12'],
        scheme="http",
        port=9200,
     )


my_index = "bluestore-meta-per-obj-index"
if not es.indices.exists(my_index):

    request_body = {
        "settings" : {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    res = es.indices.create(index=my_index, body=request_body)
    print ("response: '%s' " % (res))


#def listdir_fullpath(d):
#    return [os.path.join(d, f) for f in os.listdir(d)]

#path = os.getcwd()
newdoc = {}
iteration_ary = []


if len(sys.argv) > 1:
    newdoc['test_id'] = sys.argv[1]
else: 
    newdoc['test_id'] = "metadata_bytes_per_obj-" +  time.strftime('%Y-%m-%dT%H:%M:%SGMT', gmtime())
    
# parse log produced by test script

samples = []
with open('result.log', 'r') as f:
    with l in [ line.strip() for line in f.readlines() ]:
        if l.startswith('bytes per object used'):
            next_sample = int(l.split()[4])
            samples.append(next_sample)
print(samples)
# convert sample list into numpy array
sa = numpy.array(samples)
print('min = %f' % sa.min())
print('max = %f' % sa.max())
mean = sa.mean()
print('mean = %f' % mean)
pctdev = sa.std() * 100.0 / mean
print('%dev = %f' % pctdev)
if pctdev > 10.0:
    print('ERROR: percent deviation %f > 10%%' % pctdev)
    sys.exit(1)
newdoc['kb_per_obj'] = mean
newdoc['measured_at'] = time.ctime()
res = es.index(index="rados_kb_md_per_obj", doc_type='kb_md_statistics', body=newdoc)
