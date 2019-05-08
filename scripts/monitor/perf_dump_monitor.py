#! /usr/bin/python

import yaml, os, time, json, hashlib, paramiko, ast, sys
import socket, datetime, logging, rados, ipaddress, getopt
import multiprocessing
from paramiko import SSHClient
from datetime import date

def main():
#    setup_loggers("index_perf_dump", logging.DEBUG)
    arguments = argument_handler()
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
    #create mapping of each osd and the host it is deployed on
    for host in osd_metadata_list:
        if host["hostname"] not in osd_host_dict:
            osd_host_dict[host["hostname"]] = []
            osd_host_dict[host["hostname"]].append(host["id"])
        else:
            osd_host_dict[host["hostname"]].append(host["id"])


#########
            
    #for each host run the collect measurement method
    td_duration = datetime.timedelta(seconds=arguments.duration)
    print (td_duration.seconds)

    manager = multiprocessing.Manager()
    return_list = manager.list()

    monitor_status = True
    while monitor_status:
        collection_time = datetime.datetime.now()
#        elapsed_time = collection_time - start_time
        print (elapsed_time)
        
        #For each host spwan a subprocess and retrive perf dump
        process_list = []
        for host in osd_host_dict:
            p = multiprocessing.Process(target=collect_measurement, args=(remoteclient, host, osd_host_dict[host], return_list))
            process_list.append(p)

        for process in process_list:
            process.start()

        for process in process_list:
            process.join()

       # print "finished collecting sample"
        collection_delta_time = datetime.datetime.now() - collection_time
        
        #collection period - collection time delta
        remainder = datetime.timedelta(seconds=arguments.sample_period) - collection_delta_time
        elapsed_time = datetime.datetime.now() - start_time

        print ("going to sleep for %s seconds" % remainder.seconds)
        if remainder.seconds < 0:
            print ("taking too ling")
            time.sleep(remainder.seconds)
        else:
            time.sleep(remainder.seconds) #time_interval

        #if the elapsed time is greater than the specified duration quit. 
        if elapsed_time.seconds > td_duration.seconds:
            print ("all done monitoring")
            monitor_status = False
        else:
            print ("keep on monitoring")

    f = open("ceph-osd-perf-dump.txt", 'w')
    f.write(json.dumps(list(return_list), indent=1))
    f.close()

    
def collect_measurement(remoteclient, host, osd_list, return_list):
    print ("started collection") 
    perf_dump_data = {
            "_index": "ceph_perf_dump_data_index",
            "_type": "ceph_perf_dump_data",
            "_op_type": "create",
            "_source": {}
            }
    
    print ("working on host %s " % host)
        #collect the performance measurements 
    for osd in osd_list:
        
        perf_dump = remoteclient.issue_command(host, "ceph daemon osd.%s perf dump" % osd)
        tmp_doc = { "data": perf_dump }
        collection_time = datetime.datetime.now()
        tmp_doc["date"] = collection_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        tmp_doc["hostname"] = host
        tmp_doc["osd_id"] = osd
        perf_dump_data["_source"] = tmp_doc
        return_list.append(perf_dump_data)

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
            
            newstuff = ''.join(combinded_ouput)
            self.sshclient.close()
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
    
class argument_handler():
    def __init__(self):
        self.duration = 0
        self.sample_period = 0
        self.output_file=None
        
        usage = """ 
                Usage:
                    index_cbt.py -t <test id> -h <host> -p <port>
                    
                    -d or --duration - test duration
                    -s or --sample_period - sample period 
                    -o or --output_dir - output directory (default is current working directory)
                """
        try:
            opts, _ = getopt.getopt(sys.argv[1:], 'd:s:o:', ['output_file', 'duration=', 'sample_period_'])
        except getopt.GetoptError:
            print (usage) 
            exit(1)
    
        for opt, arg in opts:
            if opt in ('-d', '--duration'):
                self.duration = int(arg)
            if opt in ('-s', '--sample'):
                self.sample_period = int(arg)
            if opt in ('-o', '--output_dir'):
                self.output_dir = "./"
        
        if self.duration and self.sample_period:
            print("monitoring duration %s, Sample Period, %s" % (self.duration, self.sample_period))
        else:
            print(usage)
            print (self.duration, self.sample_period)
    #        print "Invailed arguments:\n \tevaluatecosbench_pushes.py -t <test id> -h <host> -p <port> -w <1,2,3,4-8,45,50-67>"
            exit (1)
    

        
if __name__ == '__main__':
    main()