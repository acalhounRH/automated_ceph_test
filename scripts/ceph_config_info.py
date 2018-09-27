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
    
    logger.debug(new_client.issue_command("osd tree")) 
        
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
    
    def issue_command(self, command):
        cmd = json.dumps({"prefix": command, "format": "json"})
        try:
            _, output, _ = self.cluster.mon_command(cmd, b'', timeout=6)
            return json.dumps(json.loads(output), indent=4)
        except Exception as e:
            logger.exception("Error issuing command")
            sys.exit(1)
        
        
        
        
    
if __name__ == '__main__':
    main()