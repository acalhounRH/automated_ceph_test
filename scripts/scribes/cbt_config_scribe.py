
import yaml, os, time, json, hashlib, paramiko
import socket, datetime, logging, rados
from paramiko import SSHClient

logger = logging.getLogger("index_cbt")

class cbt_config_transcriber:
    
    def __init__(self, test_id, cbt_yaml_config):
        self.test_id = test_id 
        self.config = yaml.load(open(cbt_yaml_config))   
        self.config_file = cbt_yaml_config

        
        self.new_client = ceph_client()
        self.remoteclient = ssh_remote_command()
        self.host_map = {}
        self.make_host_map()
   
    def get_host_type(self, hostname_or_ip):
                   
        node_type = "UNKNOWN"
        for k,v in self.cluster_host_to_type_map.items():
            
            if hostname_or_ip in v:
                node_type = k
        
        return node_type
    
    def make_host_map(self):
        ceph_node_map = self.new_client.issue_command("node ls")
        client_list = self.config['cluster']['clients']

        for node_type_list in ceph_node_map:
            for host in ceph_node_map[node_type_list]:
                self.host_map[host] = {}
                
                #get interface dict
                self.host_map[host]['interfaces'] = get_interfaces(self.remoteclient, host)
                #get cpuinfo dict
                self.host_map[host]['cpu_info'] = get_cpu_info(self.remoteclient, host)
                    
                self.host_map[host]['children'] = []
                for service_id in ceph_node_map[node_type_list][host]:
                    child = {}
                    child['service_type'] = node_type_list
                    child['service_id'] = service_id
                    if "mon" in node_type_list:
                        service_id = host.split('.')[0]
                    child['service_pid'] = get_ceph_service_pid(self.remoteclient, host, node_type_list, service_id)                
                    self.host_map[host]['children'].append(child)
                    
        if client_list:
            for client in client_list:
                child = {}
                child['service_type'] = "client"
                    
                if client not in self.host_map:
                    self.host_map[client] = {}                
                    #get interface dict
                    self.host_map[client]['interfaces'] = get_interfaces(self.remoteclient, client)
                    #get cpuinfo dict
                    self.host_map[client]['cpu_info'] = get_cpu_info(self.remoteclient, client)
                        
                self.host_map[client]['children'].append(child)
        print json.dumps(self.host_map, indent=4)
    
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
        
        return cpu_info_dict    
    
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
    
    
    def emit_actions(self):
        
        logger.debug("Indexing %s" % self.config_file)
        importdoc = {}
        importdoc["_index"] = "cbt_config-test1"
        importdoc["_type"] = "cbt_config_data"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = self.config
        importdoc["_source"]['test_id'] = self.test_id
        
        file_time = os.path.getmtime(self.config_file)
        file_time = datetime.datetime.fromtimestamp(file_time)
        importdoc['_source']['date'] = file_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        importdoc["_id"] = hashlib.md5(json.dumps(importdoc)).hexdigest()
        yield importdoc    
        

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
