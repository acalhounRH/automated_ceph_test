#! /usr/bin/python

import rados, os, logging, json, sys
from common_logging import setup_loggers

logger = logging.getLogger("check_cluster_status")

def main():
    
    setup_loggers("check_cluster_status", logging.DEBUG)
    new_client = ceph_client()
    
    
    ceph_status = new_client.issue_command("status")
    
    print json.dumps(ceph_status, indent=4)
    
    if ceph_status['health']['status'] is "HEALTH_OK":
        logger.info("Cluster health OK")
        sys.exit(0)
    elif ceph_status['health']['status'] is "HEALTH_WARN":
        checks_status = ceph_status['health']['checks']
        print checks_status
        if ceph_status['health']['checks']['TOO_FEW_PGS']:
             logger.warn(ceph_status['health']['checks']['summary']['TOO_FEW_PGS']['message'])
             sys.exit(0)
        else:
            checks_status = ceph_status['health']['checks'] 
            logger.error("HEALTH_WARN - %s" % checks_status['summary']['message'])
            sys.exit(1)
    else:
        logger.error("%s - %s" % (ceph_status['health']['status'], ceph_status['health']['checks']['summary']['message']))
        sys.exit(1)
    

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