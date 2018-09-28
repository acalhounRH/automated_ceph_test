#! /usr/bin/python

import rados

import sys
import os
import logging
import json, yaml
import getopt
import socket
from paramiko import SSHClient
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
            job_file_dict = yaml.load(open(arg))    
    
    new_client = ceph_client()
    
    raw_osd_tree = new_client.issue_command("osd tree")     
    ceph_status = new_client.issue_command("status")
    ceph_df = new_client.issue_command("df")
    
    if job_file_dict:
        total_storage_size = ceph_df['stats']['total_bytes']
        new_modifer = cbt_rbd_modifer(job_file_dict, total_storage_size)
    else:
        logger.warn("not modifying cbt job file")
    
    setup_loggers(logging.DEBUG)
    
    new_modifer.modify_job_file()
    
    #print json.dumps(raw_osd_tree, indent=1)
    osd_host_list = []
    osd_dict = {}
    for i in raw_osd_tree['nodes']:
        if "host" in i['type']:
            osd_host_list.append(i)
            print json.dumps(i, indent=1)
        if "osd" in i['type']:
            id = i['id']
            osd_dict[id] = i
    mod_list = []
    for j in osd_host_list:
        new_host_map = j
        for k in j['children']:
            index_position = new_host_map['children'].index(k)
            new_host_map['children'][index_position] = osd_dict[k]  
            print json.dumps(new_host_map, indent=4)
        mod_list.append(new_host_map)
            
   
    sshclient = SSHClient()
    
    
    for host in osd_host_list:
        hostname = host['name']
        print hostname
        ipaddress = socket.gethostbyname(hostname)
        print ipaddress
        fqdn = socket.gethostbyaddr(ipaddress)[0]
        print fqdn
        
        try:
            #sshclient.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sshclient.connect(fqdn, username="root", key_filename= "~/.ssh/authorized_keys"
            stdin, stdout, stderr = client.exec_command(socket.gethostname())
            
            print stdout
        except Exception as e:
            logger.error("Connection Failed: %s" % e)
            
        
   
   
   # print json.dumps(ceph_status, indent=1)
   # print json.dumps(ceph_df, indent=1)
    
    print "Total size is %s" % total_storage_size    
    
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
        
class cbt_rbd_modifer():
    """
        cbt__rbd_modifer updates the cbt rbd benchmark
    """
    def __init__(self, yaml_dict, total_size):
        self.job_file =  yaml_dict
        self.total_size = total_size
        
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
    
    def calculate_vol_size(self, total_storage, clients, numb_vol, replication_numb):
        """
            This method will calculate the vol_size form the total storage, 
            number of clients, and number of volumes per client. 
            
            this is a helper function that ensures the ceph cluster is populated at least to 50% of capacity 
        """
        
        percent_of_total = ( total_storage / replication_numb ) * .40
        vol_size_bytes = ( (percent_of_total / clients ) / numb_vol )
        vol_size_megabytes = (vol_size_bytes / 1024) / 1024
        
        return self.nearest_power_of_2(vol_size_megabytes) 
    
    def modify_job_file(self):
        
        numb_clients = 0
        for i in self.job_file['cluster']['clients']:
            numb_clients += 1
        
        
        pool_profile = self.job_file['benchmarks']['librbdfio']['pool_profile']
        replication_number = self.job_file['cluster']['pool_profiles'][pool_profile]['replication']
        vol_per_clients = self.job_file['benchmarks']['librbdfio']['volumes_per_client']
        
        
        vol_size = self.calculate_vol_size(self.total_size, numb_clients, vol_per_clients, replication_number)
        
        self.job_file['benchmarks']['librbdfio']['vol_size'] = vol_size
        
        print yaml.dump(self.job_file)
        
        
        
if __name__ == '__main__':
    main()