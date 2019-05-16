#!/bin/bash +x

# this script implements the Jenkins job by the same name,
# just call it in the "Execute shell" field 
# in the job configuration
# because bash doesn't throw exceptions, 
# the script doesn't stop automatically because of a 
# fatal error, we have to check for errors and exit 
# with an error status if one is seen, 
# Jenkins will stop the pipeline immediately,
# this makes troubleshooting a pipeline much easier for the user

script_dir=$HOME/automated_ceph_test

hostname | grep -q linode.com
if [ $? = 0 ]; then
	inventory_file=$HOME/ceph-linode/ansible_inventory
	linode_deploy=true
else
	inventory_file=$script_dir/ansible_inventory
fi
export ANSIBLE_INVENTORY=$inventory_file

if [[ $settings =~ .*"smallfile".* ]]; then
	echo "Settings up for smallfile test"
	mon_port=6789
	mountpoint=/mnt/cephfs
	NOTOK=1
	
	# get monitor IP address, we'll need that to mount Cephfs
	# find out about first monitor
	first_mon=`ceph -s -f json | jq .monmap.mons[0].addr`; 
	mon_ip=`echo "${first_mon//\"}" | cut -f1 -d ":"`
	echo "************ $first_mon *************"
	echo "distribute client key to Cephfs clients in expected format"
	
	 #awk '/==/{ print $NF }' /etc/ceph/ceph.client.admin.keyring > /etc/ceph/cephfs.key && \
	(rm -f /etc/ceph/cephfs.key && \
	 awk '/==/{ print $NF }' /etc/ceph/ceph.client.admin.keyring > /etc/ceph/cephfs.key && \
	 ansible -m copy -a 'src=/etc/ceph/cephfs.key dest=/etc/ceph/' clients) \
	  || exit $NOTOK
	
	# it's ok if unmounting fails because it's not already mounted
	ansible -m shell -a "umount -v $mountpoint" clients
	
	# if we can't mount Cephfs, bail out right away
	echo "create mount point"
	ansible -m shell -a "mkdir -pv $mountpoint" clients 
	echo "mount cephfs"
	ansible -m shell -a "mount -v -t ceph -o name=admin,secretfile=/etc/ceph/cephfs.key $mon_ip:$mon_port:/ $mountpoint" clients
	echo "create smf on top of mount point"
	ansible -m shell -a "mkdir -pv $mountpoint/smf" clients \
	   || exit $NOTOK
	
	echo "mount cephfs from test driver as well"
	umount $mountpoint
	(mkdir -pv $mountpoint && \
	 mount -v -t ceph -o name=admin,secretfile=/etc/ceph/cephfs.key $mon_ip:$mon_port:/ $mountpoint && \
	 mkdir -pv $mountpoint/smf ) \
	 || exit $NOTOK
fi

source /etc/profile.d/pbench-agent.sh

#seting up cbt jobfile
mkdir -p $HOME/cbt/jenkins_jobfiles/
jobfiles_dir=$HOME/cbt/jenkins_jobfiles/
echo "$settings" > $jobfiles_dir/automated_test.yml
#add host to jobfile 
$script_dir/scripts/utils/addhost_to_jobfile.sh $jobfiles_dir/automated_test.yml $inventory_file

echo "################Jenkins Job File################"
cat $jobfiles_dir/automated_test.yml

#create archive directory and run cbt test
sudo mkdir -m 777 $archive_dir
$HOME/cbt/cbt.py $jobfiles_dir/automated_test.yml -a $archive_dir

#echo "role_to_hostnames [ " > $archive_dir/results/ansible_facts.json
#ansible all -m setup -i $inventory_file | sed -s 's/ | SUCCESS => /"&/' | sed -s 's/ | SUCCESS => /": /' | sed -s 's/},/}/' | sed -s 's/}/},/' >> $archive_dir/results/ansible_facts.json
#echo "]" >> $archive_dir/results/ansible_facts.json
