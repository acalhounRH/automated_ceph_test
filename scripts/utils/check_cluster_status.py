#! /usr/bin/python

import rados, os, logging, json, sys
import logging as logger

def main():
    
    logger.basicConfig(level=logging.DEBUG)
    new_client = ceph_client()
    ceph_status = new_client.issue_command("status")
    health_status = ceph_status['health']
    health_stat = _finditem(health_status, "status")
    health_message = _finditem(health_status, "message")
    if "HEALTH_OK" in health_stat:
        logger.info("Cluster health OK")
        sys.exit(0)
    elif "HEALTH_WARN" in health_stat:
        if "too few PGs per OSD" in health_message:
             logger.warn("%s - %s" % (health_stat, health_message))
             sys.exit(0)
        else:
            logger.error("%s - %s" % (health_stat, health_message))
            sys.exit(1)
    else:
        logger.error("%s - %s" % (health_stat, health_message))
        sys.exit(1)
    
    print json.dumps(ceph_status, indent=4)
    
def _finditem(obj, key):
   if key in obj: 
       return obj[key]
   for k, v in obj.items():
       if isinstance(v,dict):
           return _finditem(v, key)
           
class ceph_client():
    def __init__(self):
        
        if not os.path.exists("/etc/ceph/ceph.conf"):
            logger.error("/etc/ceph/ceph.conf does not exist")
        
            
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

