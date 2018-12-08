import os, sys, json, time, types, csv, copy
import logging, statistics, yaml 
import datetime, socket
from scribes import *

logger = logging.getLogger("index_cbt")

def analyze_cbt_Pbench_data(tdir, cbt_config_obj, test_metadata):

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
                        tool = pfname.split("/")[-3]
                        metadata['ceph_benchmark_test']['common']['hardware']['hostname'] = hostname
                        try:
                            metadata['ceph_benchmark_test']['common']['hardware']['ipaddress'] = socket.gethostbyname(hostname)
                        except:
                            metadata['ceph_benchmark_test']['common']['hardware']['ipaddress'] = "UNKNOWN"
                        metadata['ceph_benchmark_test']['application_config']['ceph_config']['ceph_node_type'] = cbt_config_obj.get_host_type(hostname)
                        metadata['ceph_benchmark_test']['common']['test_info']['tool'] = tool
                        metadata['ceph_benchmark_test']['common']['test_info']['file_name'] = os.path.basename(pfname)
                    
                        pb_transcriber_generator = cbt_pbench_scribe.pbench_transcriber(pfname, metadata, cbt_config_obj)
                        yield pb_transcriber_generator
        else:
            logger.warn("Pbench directory not Found, %s does not exist." % host_dir_fullpath)