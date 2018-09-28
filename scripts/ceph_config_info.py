#! /usr/bin/python

import rados
import sys
import os
import logging
import json, yaml
import getopt
import socket
import paramiko
from paramiko import SSHClient
from util.common_logging import setup_loggers
from elasticsearch import client

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
    
    setup_loggers(logging.DEBUG)
    new_client = ceph_client()
    remoteclient = ssh_remote_command()
    
    #raw_osd_tree = new_client.issue_command("osd tree")
    #ceph_status = new_client.issue_command("status")
    ceph_node_map = new_client.issue_command("node ls")
    #print json.dumps(ceph_node_map, indent=4)
    ceph_df = new_client.issue_command("df")
    
    if job_file_dict:
        total_storage_size = ceph_df['stats']['total_bytes']
        new_modifer = cbt_rbd_modifer(job_file_dict, total_storage_size)
        new_modifer.modify_job_file()
    else:
        logger.warn("not modifying cbt job file")
    
    host_map = {}
    for node_type_list in ceph_node_map:
        for host in ceph_node_map[node_type_list]:
            host_map[host] = {}
            
            #get interface dict
            host_map[host]['Interfaces'] = get_interfaces(remoteclient, host)
            #get cpuinfo dict
            get_cpu_info(remoteclient, host)
                
            host_map[host]['children'] = []
            for service_id in ceph_node_map[node_type_list][host]:
                child = {}
                child['service_type'] = node_type_list
                child['service_id'] = service_id
                if "mon" in node_type_list:
                    service_id = host.split('.')[0]
                child['service_pid'] = get_ceph_service_pid(remoteclient, host, node_type_list, service_id)                
                host_map[host]['children'].append(child)

    print json.dumps(host_map, indent=4)
    
def get_cpu_info(remoteclient, host):
    output = remoteclient.issue_command(host, "lscpu")
    cpu_info_dict = {}
    
    for line in output:
        #print line
        seperated_line = line.split(":")
        #print seperated_line
        cpu_prop = seperated_line[0].strip()
        cpu_prop_value = seperated_line[1].strip()
        
        if "NUMA node" in cpu_prop and "CPU(s)" in cpu_prop:
            cpu_info_dict[cpu_prop] = []
            split_values = cpu_prop_value.split(",")
            for value in split_values:
                cpu_info_dict[cpu_prop].append(value)
        elif "Flags" not in cpu_prop:
            cpu_info_dict[cpu_prop] = cpu_prop_value  
        
    print json.dumps(cpu_info_dict, indent=4)
    
def get_interfaces(remoteclient, host):
    output = remoteclient.issue_command(host, "ip a")
    interface_dict = {}
    for line in output:
        seperated_line = line.split(" ")
        
        #Get interface name
        if seperated_line[0].strip(":").isdigit():
            interface_name = seperated_line[1]
            interface_dict[interface_name] = []
        
        #Get IPv4 for interface 
        if "inet" in line and not "inet6" in line:
            ipindex = seperated_line.index("inet") + 1
            ip_address = seperated_line[ipindex]
            interface_dict[interface_name].append(ip_address)
        
    #return a dict of all interfaces:IPaddresses
    return interface_dict

def get_ceph_service_pid(remoteclient, host, service, id):
    pid_grep_command = "ps -eaf | grep %s | grep 'id %s ' | grep -v grep| awk '{print $2}'" % (service, id)
    output = remoteclient.issue_command(host, pid_grep_command)
    return output[0]
    
    
class ssh_remote_command():
    def __init__(self):
          self.sshclient = SSHClient()
    
    def issue_command(self, host, command):
        
        try:
            self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key_path = os.path.expanduser("~/.ssh/authorized_keys")
            self.sshclient.connect(host, username="root", key_filename=key_path)
            stdin, stdout, stderr = self.sshclient.exec_command(command)
            
            #SSprint stdin.readlines()
            
            output = stdout.readlines()
            #remove trailing \n
            formated_output = []
            for i in output:
                formated_output.append(i.strip('\n'))
                
            return formated_output
        
        except Exception as e:
            logger.error("Connection Failed: %s" % e)
    
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