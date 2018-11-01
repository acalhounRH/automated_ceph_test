#!/usr/bin/bash

#pull in ansible inventory file
inventory_file=$1

#install cosbench on localhost
cd ~/
git clone https://github.com/intel-cloud/cosbench.git
cd cosbench
chmod +x *.sh

#create cosbench configuration file. 
#controler.
#add controller template to temporary configuration file
 
driver_counter=0
#loop through all client host in inventory file
for i in `ansible --list-host -i $inventory_file clients |grep -v hosts | grep -v ":"`
    do
    	#handle using ceph-linode
		if [ "$linode_cluster" == "true" ]; then
	    	IP_address=`cat $inventory_file | grep $i | awk {'print $2'} | sed 's/.*=//'`
	    	$driver_name=$IP_address
	    #handle non ceph-linode seting, i.e. known host
		else
 	   		$driver_name=$i
	    fi
	    
	driver_temptlate="
	[driver${driver_counter}]
    name = driver${driver_counter}
    url = http://${driver_name}:18088/driver
	"
	#append new client driver info to temp configuration file
	echo >> driver.tmp
	driver_counter=$((driver_counter+1)
done

#setup templates for cosbench controller and drivers
controller_template="
	[controller]
    drivers = 2
    log_level = INFO
    log_file = log/system.log
    archive_dir = archive
"
echo controller_template > controller.conf.tmp

cat driver.tmp >> controller.conf.tmp


#install cosbench on all clients 
ansible -m shell -a "git clone https://github.com/intel-cloud/cosbench.git; cd cosbench; chmod +x *.sh" -i $inventory_file clients

#setup driver conf file
remotedriver_template="
	[driver]
    log_level = INFO
    url = http://127.0.0.1:18088/driver
"

#make driver.conf file and copy it to all client host 
echo > driver.conf
ansible -m copy -a "src=driver.conf des=/cosbench/release/conf/driver.conf" -i $inventory_file clients
