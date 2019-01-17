#! /usr/bin/python

import yaml, os, time, json, hashlib, paramiko, ast
import socket, datetime, logging, rados, ipaddress
from paramiko import SSHClient
from datetime import date

logger = logging.getLogger("index_cbt")

def main():
    #setup client connection to ceph
    acitve_ceph_client = ceph_client()
    #setup ssh remote command 
    remoteclient = ssh_remote_command()
    
    #get metadata list of all osds
    osd_metadata_list = acitve_ceph_client.issue_command("osd metadata")
    
    start_time = datetime.datetime.now() 
    elapsed_time = 0 
    
    host_list = []
    osd_host_dict = {}
    for host in osd_metadata_list:
        if host["hostname"] not in osd_host_dict:
            osd_host_dict[host["hostname"]] = []
            osd_host_dict[host["hostname"]].append(host["id"])
        else:
            osd_host_dict[host["hostname"]].append(host["id"])
            
#    print json.dumps(osd_host_dict, indent=4)
    
    for host in osd_host_dict:
     collect_measurement(remoteclient, host, osd_host_dict[host], 1, 60, start_time)
        
def collect_measurement(remoteclient, host, osd_list, duration, time_interval, start_time):
    
    perf_dump_data = {
            "_index": "ceph_perf_dump_data_index",
            "_type": "ceph_perf_dump_data",
            "_op_type": "create",
            "_source": {}
            }
    
    elapsed_time = datetime.timedelta(seconds=0)
    print "working on host %s " % host
    td_duration = datetime.timedelta(seconds=duration)
    print td_duration.seconds
    f = open("perf-dump.txt", 'w')
    while elapsed_time.seconds < td_duration.seconds:
        collection_time = datetime.datetime.now() 
        elapsed_time = collection_time - start_time
        print elapsed_time
        
        #collect the performance measurements 
        for osd in osd_list:
            print "osd %s" % osd
            perf_dump = remoteclient.issue_command(host, "ceph daemon osd.%s perf dump" % osd)   
            #print perf_dump
            f.write(json.dumps(perf_dump, indent=4))
            print json.dumps(perf_dump, indent=4)
        #sleep after you have collected perf dump
        #collection_delta_time = collection_time - datetime.datetime.now()
        collection_delta_time = datetime.datetime.now() - collection_time
#        print collection_delta_time
#        print time_interval
#        print datetime.timedelta(seconds=time_interval)
#        print collection_delta_time.seconds
        remainder = datetime.timedelta(seconds=time_interval) - collection_delta_time
        
        print "going to sleep for %s" % remainder.seconds
        if remainder.seconds < 0:
            print "taking too ling"
            time.sleep(remainder.seconds)
        else: 
            time.sleep(remainder.seconds) #time_interval
    f.close()

class ssh_remote_command():
    def __init__(self):
          self.sshclient = SSHClient()
    
    def issue_command(self, host, command):
        combinded_ouput = []
        try:
            self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key_path = os.path.expanduser("~/.ssh/authorized_keys")
            self.sshclient.connect(host, username="root", key_filename=key_path)
            stdin, stdout, stderr = self.sshclient.exec_command(command)
            
            output = stdout.readlines()

            for line in output:
                combinded_ouput.append(line.strip())
            #newstuff = "[%s]" % ''.join(combinded_ouput)
            newstuff = ''.join(combinded_ouput)
#            print newstuff
            self.sshclient.close()
#            output = ''.join(output)
#            output = output.strip()
#            return output
            brandnewstuff = ast.literal_eval(newstuff)
            return brandnewstuff
        
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
