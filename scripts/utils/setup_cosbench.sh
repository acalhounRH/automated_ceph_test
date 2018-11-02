#!/usr/bin/bash

#pull in ansible inventory file
inventory_file=$1
linode_cluster="true"

#install cosbench on localhost

yum install nc -y
cd ~/
if [ ! -d cosbench ]; then
	mkdir cosbench; cd cosbench
	wget https://github.com/ekaynar/Benchmarks/raw/master/cosbench/v0.4.2.tar.gz
	tar xzf v0.4.2.tar.gz
	cd ~/cosbench/v0.4.2/
	chmod +x *.sh
fi 

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
	    	driver_name=$IP_address
	    #handle non ceph-linode seting, i.e. known host
		else
 	   		driver_name=$i
	    fi
	    
	driver_template="
	[driver${driver_counter}]
    name = driver${driver_counter}
    url = http://${driver_name}:18088/driver
	"
	#append new client driver info to temp configuration file
	echo "$driver_template" >> driver.tmp
	driver_counter=$((driver_counter+1))
done

#setup templates for cosbench controller and drivers
controller_template="
	[controller]
    drivers = $driver_counter
    log_level = INFO
    log_file = log/system.log
    archive_dir = archive
"

echo "$controller_template" > conf/controller.conf
cat driver.tmp >> conf/controller.conf
echo > driver.tmp

#install cosbench on all clients
ansible -m shell -a "yum install wget -y; yum install java -y; yum install nc -y" -i $inventory_file clients

ansible -m shell -a "mkdir cosbench; \
					cd cosbench; \
					wget https://github.com/ekaynar/Benchmarks/raw/master/cosbench/v0.4.2.tar.gz; \
					tar xzf v0.4.2.tar.gz; \
					cd v0.4.2; chmod +x *.sh " -i $inventory_file clients

ansible -m shell -a "cd ~/cosbench/v0.4.2/; ./start-driver.sh" -i $inventory_file clients


./start-controller.sh

##setup driver conf file
#remotedriver_template="
#	[driver]
#    log_level = INFO
#    url = http://127.0.0.1:18088/driver
#"
#
##make driver.conf file and copy it to all client host 
#echo > driver.conf
#ansible -m copy -a "src=driver.conf dest=/cosbench/release/conf/driver.conf" -i $inventory_file clients
