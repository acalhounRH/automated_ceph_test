
import yaml, os, time, json, hashlib
import socket, datetime, logging

logger = logging.getLogger("index_cbt")

class cbt_config_transcriber:
    
    def __init__(self, test_id, cbt_yaml_config):
        self.test_id = test_id 
        self.config = yaml.load(open(cbt_yaml_config))
        
        self.config_file = cbt_yaml_config
        self.cluster_host_to_type_map = {}
        self.map_node_types_hostnames()

    def map_node_types_hostnames(self):
        host_type_list = ["osds", "mons", "clients"]
        self.cluster_host_to_type_map['osds'] = []
        self.cluster_host_to_type_map['mons'] = []
        self.cluster_host_to_type_map['clients'] = []
                        
        for host_type in host_type_list:
                for name in self.config['cluster'][host_type]:
                    try:
                        #socket.inet_aton(name)
                        self.cluster_host_to_type_map[host_type].append(socket.gethostbyaddr(name))
                    except:
                        self.cluster_host_to_type_map[host_type].append(name)
    
    def get_host_type(self, hostname_or_ip):
                   
        node_type = "UNKNOWN"
        for k,v in self.cluster_host_to_type_map.items():
            
            if hostname_or_ip in v:
                node_type = k
        
        return node_type
    
    def emit_actions(self):
        
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