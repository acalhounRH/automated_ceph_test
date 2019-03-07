
import yaml, os, time, json, hashlib, paramiko
import socket, datetime, logging, rados, ipaddress
from paramiko import SSHClient
from elasticsearch.client.remote import RemoteClient

logger = logging.getLogger("index_cbt")

class cbt_config_transcriber:
    
    def __init__(self, UID, cbt_yaml_config, hostmap=None):
        self.UID = UID 
        self.config = yaml.load(open(cbt_yaml_config))   
        self.config_file = cbt_yaml_config
        self.host_map = {}
        self.fqdn_map = {}
        self.cpu_info_map = {}
        self.interface_map = {}
        
        if hostmap:
            self.load_host_map(hostmap)
        else:    
            #if hostmap file is not provided generate it  
            self.acitve_ceph_client = ceph_client()   
             
            if self.acitve_ceph_client.Connection_status:   
                self.remoteclient = ssh_remote_command()
        
                
                self.make_host_map()
            else:
                logger.warn("Ceph host to role mapping was not performed.")
                
    def load_host_map(self, hostmap_file):
        logger.info("Loading %s" % hostmap_file)
        #print hostmap_file
        with open(hostmap_file) as f:
            self.host_map = json.loads(f.read())
        
        #print json.dumps(self.host_map, indent=4)
            
    def set_host_type_list(self):
        
        host_type_list = ""
        
        for host in self.host_map:
            host_type_list = ""
            for child in self.host_map[host]['children']:
                if child['service_type'] not in host_type_list:
                    host_type_list += "%s," % str(child['service_type'])
                    
            self.host_map[host]['host_type_list'] = host_type_list
    
    def get_host_info(self, hostname_or_ip):
        
        empty_dict = {}
        if self.acitve_ceph_client.Connection_status:
            host_fqdn = self.get_fqdn(self.remoteclient, hostname_or_ip)
            if host_fqdn is not None:
                for host in self.host_map:
                    if host_fqdn in host:
                        return self.host_map[host]
            else: 
                return empty_dict               
        else:
            return empty_dict
        
    def get_host_type(self, host):
        
        if self.acitve_ceph_client.Connection_status:
            try:
                host_fqdn = self.get_fqdn(self.remoteclient, host)
                host_info = self.get_host_info(host_fqdn)
                return host_info['host_type_list']
            except:
                return "UNKNOWN"
        else:
            return "UNKOWN"
        
    def make_host_map(self):
        logger.debug("getting ceph node map")
        ceph_node_map = self.acitve_ceph_client.issue_command("node ls")
        logger.debug("getting client list")
        client_list = self.config['cluster']['clients']
        
        ceph_role_list = ['mds', 'mon', 'osd', 'mgr']
        for role in ceph_role_list:
            host_role_list = self.acitve_ceph_client.issue_command("%s metadata" % role)
            #print json.dumps(host_role_list, indent=4)
            
            if len(host_role_list) > 0:
                for role_info in host_role_list:
                    logger.debug("host role: %s" % role)
                    logger.debug(json.dumps(role_info, indent=1))
                    #print role_info['hostname']
                    host_fqdn = self.get_fqdn(self.remoteclient, role_info['hostname'])
                    
                    child = {}
                    child['service_type'] = role
                    
#                     if "mon" in role:
#                         service_id = str(role_info['name'])
#                     elif "osd" in role or "mgr" in role:
#                         service_id = str(role_info['id'])

                    if "id" in role_info:
                        service_id = str(role_info['id'])
                    elif "name" in role_info:
                        service_id = str(role_info['name'])
                    else:
                        service_id = "UNKNOWN"
                        
                    child['service_id'] = service_id
                    child['service_pid'] = self.get_ceph_service_pid(self.remoteclient, host_fqdn, role, service_id)                
                    
                    if host_fqdn not in self.host_map:
                        self.host_map[host_fqdn] = {}
                        self.host_map[host_fqdn]['children'] = [] 
                        #get interface dict
                        self.host_map[host_fqdn]['interfaces'] = self.get_interfaces(self.remoteclient, host_fqdn)
                        #get cpuinfo dict
                        self.host_map[host_fqdn]['cpu_info'] = self.get_cpu_info(self.remoteclient, host_fqdn)
                        
                    if child not in self.host_map[host_fqdn]['children']:
                        self.host_map[host_fqdn]['children'].append(child)
                    
        
        if client_list:
            for client in client_list:
                
                client_fqdn = self.get_fqdn(self.remoteclient, client)
                
                if client_fqdn is not None:
                    child = {}
                    child['service_type'] = "client"
                    child['service_pid'] = "-1"
                    child['service_id'] = -1
                        
                    if client_fqdn not in self.host_map:
                        self.host_map[client_fqdn] = {}                
                        self.host_map[client_fqdn]['children'] = []
                        try:
                            #get interface dict
                            self.host_map[client_fqdn]['interfaces'] = self.get_interfaces(self.remoteclient, client_fqdn)
                            #get cpuinfo dict
                            self.host_map[client_fqdn]['cpu_info'] = self.get_cpu_info(self.remoteclient, client_fqdn)
                        except:
                            logger.debug("unable to reach client - %s" % client_fqdn) 
                    
                    
                        
                    self.host_map[client_fqdn]['children'].append(child)
        self.set_host_type_list()
        
        dataWriter = open("host_map.json", 'w')
        dataWriter.write(json.dumps(self.host_map, indent=4))
        dataWriter.close()
            
        #print json.dumps(self.host_map, indent=4)
        
    def get_fqdn(self, remoteclient, host):
        
        if host in self.fqdn_map:
            output = self.fqdn_map[host]
            return output
        else:
            try:
                output = remoteclient.issue_command(host, "hostname -f")
                output = output[0].strip()
                self.fqdn_map[host] = output
                return output
            except:
                return None
        
    def get_cpu_info(self, remoteclient, host):
        cpu_info_dict = {}
        
        if host in self.cpu_info_map:
            cpu_info_dict = self.cpu_info_map[host]
            return cpu_info_dict 
        else:
            try:
                output = remoteclient.issue_command(host, "lscpu")
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
            
            except:
                logger.warn("Unable to retrive cpu info for %s" % host)
            
            self.cpu_info_map[host] = cpu_info_dict
            return cpu_info_dict    
    
    def get_interfaces(self, remoteclient, host):
        interface_dict = {}
        
        if host in self.interface_map:
            interface_dict = self.interface_map[host]
            return interface_dict
        else:
            try:
                output = remoteclient.issue_command(host, "ip a")
                
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
            except:
                logger.warn("Unable to retrive network in for %s" % host)
            self.interface_map[host] = interface_dict    
            #return a dict of all interfaces:IPaddresses
            return interface_dict

    def get_ceph_service_pid(self, remoteclient, host, service, id):
        pid_grep_command = "ps -eaf | grep %s | grep 'id %s ' | grep -v grep| awk '{print $2}'" % (service, id)
        output = remoteclient.issue_command(host, pid_grep_command)
        if output:
            return output[0]
        else:
            return str("-1")
    
    def emit_actions(self):
        
        logger.debug("Indexing %s" % self.config_file)
        importdoc = {}
        importdoc["_index"] = "cbt_config-test1"
        importdoc["_type"] = "cbt_config_data"
        importdoc["_op_type"] = "create"
        importdoc["_source"] = { 'ceph_benchmark_test': 
                                { "common": 
                                 { 
                                     "test_info": 
                                     { 
                                         "test_id": self.UID }
                                     }
                                 }, 
                              #  "ceph_config": self.host_map,
                                "cbt_config": self.config
                                }
        #importdoc["_source"]['ceph_benchmark_test']['cbt_config'] = self.config
        #importdoc["_source"]['ceph_benchmark_test']['test_id'] = self.test_id
        
        file_time = os.path.getmtime(self.config_file)
        file_time = datetime.datetime.fromtimestamp(file_time)
        importdoc['_source']['date'] = file_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        importdoc["_id"] = hashlib.md5(str(importdoc).encode("base64","strict")).hexdigest()
        yield importdoc    
        

class ssh_remote_command():
    def __init__(self):
          self.sshclient = SSHClient()
    
    def issue_command(self, host, command):
        
        try:
            self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
            #pkey = paramiko.RSAKey.from_private_key_file(key_path)
            self.sshclient.connect(host, username="root", key_filename=key_path)
            stdin, stdout, stderr = self.sshclient.exec_command(command)
            
            if stderr:
                raise ValueError(str(stderr))
            
            output = stdout.readlines()
            #remove trailing \n
            formated_output = []
            for i in output:
                formated_output.append(i.strip('\n'))
            
            self.sshclient.close()
            return formated_output
        
        except Exception as e:
            self.sshclient.close()
            logger.warn("SSH Connection Failed: %s" % e)
    
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
                logger.warn("Ceph Client Connection error: %s" % e.message )
            
                
            self.osd_host_list = []
            self.osd_list = []
        
    def issue_command(self, command):
        cmd = json.dumps({"prefix": command, "format": "json"})
        try:
            _, output, _ = self.cluster.mon_command(cmd, b'', timeout=6)
            return json.loads(output)
        except Exception as e:
            logger.error("Error issuing command, %s" % command)
