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

    cluster = rados.Rados(conffile="/etc/ceph/ceph.conf",
                          conf=dict(keyring='/etc/ceph/ceph.client.admin.keyring'),
                          )
    try:
        cluster.connect()
    except Exception as e:
        logger.exception("Connection error: %s" % e.strerror )
        
    cmd = json.dumps({"prefix": "osd tree", "format": "json"})
    _, output, _ = cluster.mon_command(cmd, b'', timeout=6)
    logger.debug(json.dumps(json.loads(output), indent=4))
    #return json.dumps(json.loads(output), indent=4)
    
    
    
    
if __name__ == '__main__':
    main()