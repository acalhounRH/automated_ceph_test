import os
import linode.api as linapi
import binascii, logging, socket, time

linode_log = logging.getLogger("linode")
linode_log.setLevel(logging.CRITICAL)
urllib3_log = logging.getLogger("urllib")
urllib3_log.setLevel(logging.CRITICAL)



def main ():
    # Constants below determined from the results of the avail_foo() API commands
    DATACENTER = "Newark"
    DISTRIBUTION = "CentOS 7"
    KERNEL = "Latest 64 bit"
    SSH_PUBLIC_KEY_FILE = os.getenv("HOME") + "/.ssh/id_rsa.pub"
    with open(SSH_PUBLIC_KEY_FILE) as f:
        SSH_KEY = f.read()


    # Disk parameters
    SWAP_LABEL="swap"
    SWAP_SIZE_MB=256

    BOOT_LABEL='root'
    DISK_SIZE_GB=24
    BOOT_SIZE=DISK_SIZE_GB*1024-SWAP_SIZE_MB


    client = linapi.Api(os.environ['LINODE_API_KEY'])

    datacenters = client.avail_datacenters()
    plans = client.avail_linodeplans()
    distributions = client.avail_distributions()
    kernels = client.avail_kernels()
    
    datacenter = filter(lambda d: d[u'LOCATION'].lower().find(DATACENTER.lower()) >= 0, datacenters)[0][u'DATACENTERID']
    distribution = filter(lambda d: d[u'LABEL'].lower().find(DISTRIBUTION.lower()) >= 0, distributions)[0][u'DISTRIBUTIONID']
    kernel = filter(lambda k: k[u'LABEL'].lower().find(str(KERNEL).lower()) >= 0, kernels)[0][u'KERNELID']

    disk = []
    plan = filter(lambda p: p[u'LABEL'].lower().find("8") >= 0, plans)[0]
#    print plan
    #for i in plans:
    #    print i

    running = client.linode_list()

    #for i in running:
    #    print i
    active = filter(lambda x: x[u'LABEL'] == "Jenkins_Agent" and x[u'LPM_DISPLAYGROUP'] == "Jenkins", running)

    if active:
        print "jenkins agent already created"
    else:
#        print "Createing Jenkins agent"
#        print "Create linode"
        node = client.linode_create(DatacenterID = datacenter, PlanID = plan[u'PLANID'], PaymentTerm = 1)
#        print "set label and group"
        client.linode_update(LinodeID = node[u'LinodeID'], Label = 'Jenkins_Agent', lpm_displayGroup = 'Jenkins', watchdog = 1, Alert_cpu_enabled = 0)
#        print "create private IP"
        client.linode_ip_addprivate(LinodeID = node[u'LinodeID'])
#        print "get ips"
        ips = client.linode_ip_list(LinodeID = node[u'LinodeID'])
        ip_private = filter(lambda ip: not ip[u'ISPUBLIC'], ips)[0][u'IPADDRESS']
        ip_public = filter(lambda ip: ip[u'ISPUBLIC'], ips)[0][u'IPADDRESS']
#       print "create disk and sshkey for root"
       
        current_disks = client.linode_disk_list(LinodeID = node[u'LinodeID'])
        configs = client.linode_config_list(LinodeID = node[u'LinodeID'])

        swap_size = 128
        root_size = int(plan['DISK'])*1024 - swap_size
        if root_size + swap_size < int(plan['DISK'])*1024:
           raw_size = int(plan['DISK'])*1024 - (root_size+swap_size)
        else:
           raw_size = 0
        disks = []
        root = filter(lambda d: d[u'LABEL'] == u'root', current_disks)
        if root:
           root = root[0]
           assert(root[u'SIZE'] == int(root_size))
           disks.append({u'DiskID': root[u'DISKID']})
        else:
           disks.append(client.linode_disk_createfromdistribution(LinodeID = node[u'LinodeID'], Label = u'root', DistributionID = distribution, rootPass = "linoj666", Size = root_size, rootSSHKey = SSH_KEY))
        swap = filter(lambda d: d[u'LABEL'] == u'swap', current_disks)
        if swap:
           swap = swap[0]
           assert(swap[u'SIZE'] == int(swap_size))
           assert(swap[u'TYPE'] == u'swap')
           disks.append({u'DiskID': swap[u'DISKID']})
        else:
           disks.append(client.linode_disk_create(LinodeID = node[u'LinodeID'], Label = u'swap', Type = u'swap', Size = swap_size))
        raw = filter(lambda d: d[u'LABEL'] == u'raw', current_disks)
        if raw:
           raw = raw[0]
           assert(raw[u'SIZE'] == int(raw_size))
           assert(raw[u'TYPE'] == u'raw')
           disks.append({u'DiskID': raw[u'DISKID']})
        elif raw_size > 0:
           disks.append(client.linode_disk_create(LinodeID = node[u'LinodeID'], Label = u'raw', Type = u'raw', Size = raw_size))
        disks = [unicode(d[u'DiskID']) for d in disks]
        disklist = u','.join(disks)

        config = client.linode_config_create(LinodeID = node[u'LinodeID'], Label = u'jenkins_agent', KernelID = kernel, Disklist = disklist, RootDeviceNum = 1)
        client.linode_boot(LinodeID = node[u'LinodeID'], ConfigID = config[u'ConfigID'])

        notdone = True
        while notdone:
            linodes = client.linode_list()
            notdone = False
            for linode in linodes:
                #print "waiting for startup..."
                if linode[u'LPM_DISPLAYGROUP'] == 'Jenkins':
                    if linode[u'STATUS'] != 1:
                        notdone = True
            time.sleep(5)



        host = socket.gethostbyaddr(ip_public)[0]
        print host



if __name__ == "__main__":
    main()


