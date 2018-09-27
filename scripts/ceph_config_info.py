#! /usr/bin/python

import rados
import paramiko
import sys
import os
import logging
import json
from util.common_logging import setup_loggers

logger = logging.getLogger("index_cbt")

def main():
    
    setup_loggers(logging.DEBUG)

    new_client = ceph_client()
    
    raw_osd_tree = new_client.issue_command("osd tree") 
        
    ceph_status = new_client.issue_command("status")
    
    ceph_df = new_client.issue_command("df")
    
    print json.dumps(ceph_status, indent=1)
    print json.dumps(ceph_status, indent=1)
    print json.dumps(ceph_df, indent=1)
   # cmd = json.dumps({"prefix": "osd tree", "format": "json"})
   # _, output, _ = cluster.mon_command(cmd, b'', timeout=6)
   # logger.debug(json.dumps(json.loads(output), indent=4))
    #return json.dumps(json.loads(output), indent=4)
    
    
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
    
        
        
        
    
if __name__ == '__main__':
    main()