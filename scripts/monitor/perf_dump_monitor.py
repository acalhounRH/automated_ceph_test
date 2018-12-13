#! /usr/bin/python

import yaml, os, time, json, hashlib, paramiko
import socket, datetime, logging, rados, ipaddress
from paramiko import SSHClient

logger = logging.getLogger("index_cbt")

def main():
    #setup client connection to ceph
    acitve_ceph_client = ceph_client()
    #setup ssh remote command 
    remoteclient = ssh_remote_command()
    
    #get metadata list of all osds
    osd_metadata_list = self.acitve_ceph_client.issue_command("osd metadata")
    
    start_time = time.time()
    elapsed_time = 0 
    
    host_list = []
    osd_host_dict = {}
    for host in osd_metadata_list:
        if host["hostname"] not in host_list:
            osd_host_dict[host["hostname"]] = []
            osd_host_dict[host["hostname"]].append(host["id"])
        else:
            osd_host_dict[host["hostname"]].append(host["id"])
            
    print json.dumps(osd_host_dict, indent=4)
        
    
    
def Collect_measurement(host, duration, time_interval):
    
    perf_dump_data = {
            "_index": "ceph_perf_dump_data_index",
            "_type": "ceph_perf_dump_data",
            "_op_type": "create",
            "_source": {}
            }
    
    while time_delta_s < duration:
        collection_time = time.time() 
        elapsed_time = collection_time - start_time
        
        #collect the performance measurements 
        for osd in osd_list:
        
          perf_dump = remoteclient.issue_command(host, "ceph daemon osd.%s perf dump" % osd)
        
            
        
        #sleep after you have collected perf dump 
        time.sleep(time_interval) #time_interval
        
    
    

class ssh_remote_command():
    def __init__(self):
          self.sshclient = SSHClient()
    
    def issue_command(self, host, command):
        
        try:
            self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key_path = os.path.expanduser("~/.ssh/authorized_keys")
            self.sshclient.connect(host, username="root", key_filename=key_path)
            stdin, stdout, stderr = self.sshclient.exec_command(command)
            
            output = stdout.readlines()
            #remove trailing \n
            formated_output = []
            for i in output:
                formated_output.append(i.strip('\n'))
            
            self.sshclient.close()
            return formated_output
        
        except Exception as e:
            self.sshclient.close()
            logger.warn("Connection Failed: %s" % e)
    
class ceph_client():
    def __init__(self):
        
        self.Connection_status = False
        
        if not os.path.isfile("/etc/ceph/ceph.conf"):
            logger.warn("/etc/ceph/ceph.conf not found!")
        elif not os.path.isfile("/etc/ceph/ceph.client.admin.keyring"):
            logger.warn("/etc/ceph/ceph.client.admin.keyring not found!")
        else:
            self.cluster = rados.Rados(conffile="/etc/ceph/ceph.conf",
                                       conf=dict(keyring='/etc/ceph/ceph.client.admin.keyring'),
                                       )
            try:
                self.cluster.connect(timeout=1)
                self.Connection_status = True
            except Exception as e:
                logger.warn("Connection error: %s" % e.message )
            
                
            self.osd_host_list = []
            self.osd_list = []
        
    def issue_command(self, command):
        cmd = json.dumps({"prefix": command, "format": "json"})
        try:
            _, output, _ = self.cluster.mon_command(cmd, b'', timeout=6)
            return json.loads(output)
        except Exception as e:
            logger.error("Error issuing command, %s" % command)
            
if __name__ == '__main__':
    main()




