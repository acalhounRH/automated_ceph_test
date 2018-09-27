#! /usr/bin/python

import rados
import paramiko
import sys
import os
import logging
import json, yaml
import getopt
from util.common_logging import setup_loggers

logger = logging.getLogger("index_cbt")

def main():
    
    job_file_dict = {}
    usage = """ 
            Usage:
                evaluatecosbench_pushes.py -t <test id> -h <host> -p <port>
                
                -j or --job_file - job file identifier
            """
    
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'j:', ['job_file'])
    except getopt.GetoptError:
        print usage 
        exit(1)

    for opt, arg in opts:
        if opt in ('-j', '--job_file'):
            job_file_dict = yaml.load(arg)    
    
    if job_file_dict :
        new_modifer = cbt_modifer(job_file_dict)
    else:
        logger.warn("not modifying cbt job file")
    
    setup_loggers(logging.DEBUG)

    new_client = ceph_client()
    
    raw_osd_tree = new_client.issue_command("osd tree") 
        
    ceph_status = new_client.issue_command("status")
    
    ceph_df = new_client.issue_command("df")
    
   # print json.dumps(ceph_status, indent=1)
   # print json.dumps(ceph_status, indent=1)
   # print json.dumps(ceph_df, indent=1)
    
    total_storage_size = ceph_df['stats']['total_bytes']
    print "Total size is %s" % total_storage_size    
    print "volume size should be nearest power of 2: %s" % new_client.calculate_vol_size(total_storage_size)

    
def argument_handler():


    
class ceph_client():
    def __init__(self):
        self.cluster = rados.Rados(conffile="/etc/ceph/ceph.conf",
                      conf=dict(keyring='/etc/ceph/ceph.client.admin.keyring'),
                      )
        try:
            self.cluster.connect()
        except Exception as e:
            logger.exception("Connection error: %s" % e.strerror )
            sys.exit(1)
            
        self.osd_host_list = []
        self.osd_list = []
    
    def issue_command(self, command):
        cmd = json.dumps({"prefix": command, "format": "json"})
        try:
            _, output, _ = self.cluster.mon_command(cmd, b'', timeout=6)
            return json.loads(output)
        except Exception as e:
            logger.exception("Error issuing command")
            sys.exit(1)
        
class cbt_modifer():
    def __init__(self, yaml_dict):
        self.job_file =  yaml_dict
        
    def nearest_power_of_2(self, raw_value):
        
        previous_value = 0
        new_value = 0

        power = 1 
        while True:
            
            new_value = 2 ** power
            if new_value > raw_value: 
                
                lower_delta = raw_value - previous_value 
                upper_delta = new_value - raw_value 
                
                if lower_delta < upper_delta:
                    return previous_value
                    break
                if upper_delta < lower_delta:
                    return new_value
                    break
            else: 
                power += 1
                previous_value = new_value
    
    def calculate_vol_size(self, total_storage, clients=3, numb_vol=8):
        """
            This method will calculate the vol_size form the total storage, 
            number of clients, and number of volumes per client. 
            
            this is a helper function that ensures the ceph cluster is populated at least to 50% of capacity 
        """
        
        replication = 3 
        percent_of_total = ( total_storage / replication ) * .40
        vol_size_bytes = ( (percent_of_total / clients ) / numb_vol )
        print vol_size_bytes
        vol_size_megabytes = (vol_size_bytes / 1024) / 1024
        print vol_size_megabytes
        
        
        return self.nearest_power_of_2(vol_size_megabytes) 
    
        
        
        
    
if __name__ == '__main__':
    main()