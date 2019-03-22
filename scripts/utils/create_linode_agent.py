import os
from linode_api4 import LinodeClient
import binascii, logging, socket, time, sys, json, binascii

linode_log = logging.getLogger("linode")
linode_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib")
urllib3_log.setLevel(logging.CRITICAL)

def status_check(node, status):
    cur_status = ""
    while cur_status != status:
        time.sleep(10)
        cur_status = node.status
    return 

def main ():
    
    agent_label = os.environ['AGENT_NAME'] 
    SSH_PUBLIC_KEY_FILE = os.getenv("HOME") + "/.ssh/id_rsa.pub"
    key = os.environ['LINODE_API_KEY']
    
    client = LinodeClient(key)
    
    try:
        node, password = client.linode.instance_create('g6-nanode-1',
                                                     region='us-east',
                                                     image='linode/centos7',
                                                     authorized_keys=SSH_PUBLIC_KEY_FILE,
                                                     label=agent_label,
                                                     group='Jenkins_Agents',
                                                     tags=['Jenkins_Agents'])
        node.ip_allocate(False)
        node.reboot()
        time.sleep(20)
        status_check(node, "running")
        host = socket.gethostbyaddr(node.ipv4[0])[0]
        print host
    except Exception as e:
        if hasattr(e, 'errors'):
            if "Label must be unique among your linodes" in e.errors:
                print "jenkins agent already created"
            else:
                sys.exit()
        else:
            sys.exit()

if __name__ == "__main__":
    main()


