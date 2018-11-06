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
inventory_file=$script_dir/ansible_inventory

echo "$ceph_inventory" > $inventory_file
if [ -d /usr/share/ceph-ansible ]; then
	echo "purging cluster and removing previous version of ceph-ansible"
	cd /usr/share/ceph-ansible
	ansible-playbook infrastructure-playbooks/purge-cluster.yml -i $inventory_file -e ireallymeanit=yes
fi

sudo yum remove ceph-ansible -y

#clearout ceph-ansible staging area 

if [ ! -d $script_dir/staging_area/rhcs_latest/ ]; then
	mkdir -p $script_dir/staging_area/rhcs_latest
    mkdir -p $script_dir/staging_area/rhcs_old
    chmod -R 777 $script_dir/staging_area/


else
	mv $script_dir/staging_area/rhcs_latest/* $script_dir/staging_area/rhcs_old/
	pwd
fi
	cd $script_dir/staging_area/rhcs_latest/
	 
sudo rm -rf /ceph-ansible-keys
sudo mkdir -m0777 /ceph-ansible-keys

#pull iso
if [[ $ceph_iso_file =~ "RHCEPH-*-x86_64-dvd.iso" ]]; then
	echo "**************$ceph_iso_file"
	sudo wget -r -nd --no-parent -A "$ceph_iso_file" $ceph_iso_path &> /dev/null
    new_ceph_iso_file="$(ls)"
else
	sudo wget $ceph_iso_path/$ceph_iso_file &> /dev/null
fi
 chmod 777 $ceph_iso_file


#mount ISO and create rhcs yum repo file 
sudo cp $script_dir/staging_area/repo_files/rhcs.repo /etc/yum.repos.d/
sudo mkdir -p /mnt/rhcs_latest/
sudo umount /mnt/rhcs_latest/
sudo mount $script_dir/staging_area/rhcs_latest/RHCEPH* /mnt/rhcs_latest/
sudo yum clean all


#install ceph-ansible
sudo yum install ceph-ansible -y

#added in order to allow installation of bluestore on lVMs
patch /usr/share/ceph-ansible/roles/ceph-osd/tasks/check_mandatory_vars.yml ~/automated_ceph_test/scripts/patches/check_mandatory_vars.patch
patch /usr/share/ceph-ansible/roles/ceph-osd/tasks/scenarios/lvm.yml ~/automated_ceph_test/scripts/lvm.patch


sudo sed -i 's/gpgcheck=1/gpgcheck=0/g' /usr/share/ceph-ansible/roles/ceph-common/templates/redhat_storage_repo.j2

mkdir -p $script_dir/staging_area/tmp
#setup all.yml
echo "$ceph_ansible_all_config" > $script_dir/staging_area/tmp/all.yml
if [[ $ceph_iso_file =~ "RHCEPH-*-x86_64-dvd.iso" ]]; then
	sed -i "s/RHCEPH.*$/$new_ceph_iso_file/g" $script_dir/staging_area/tmp/all.yml
fi
sudo cp $script_dir/staging_area/tmp/all.yml /usr/share/ceph-ansible/group_vars/all.yml


#setup osd.yml
echo "$ceph_ansible_osds_config" > $script_dir/staging_area/tmp/osds.yml
sudo cp $script_dir/staging_area/tmp/osds.yml /usr/share/ceph-ansible/group_vars/osds.yml


#copy site.yml
sudo cp /usr/share/ceph-ansible/site.yml.sample /usr/share/ceph-ansible/site.yml

$script_dir/scripts/utils/register_host.sh $inventory_file

echo "Start Ceph installation"
cd /usr/share/ceph-ansible
ANSIBLE_STRATEGY=debug; ansible-playbook -v site.yml -i $inventory_file
exit_status=$?

if [ "$exit_status" -gt "0" ]; then
	echo "ceph-ansible install failed"
	exit $exit_status
fi
	
sleep 30
yum install ceph-common -y
#save off the first mon in the inventory list, used to fetch ceph.conf file for agent host. 
for i in `ansible --list-host -i $inventory_file mons |grep -v hosts | grep -v ":"`
    do
    	monname=$i
    	break
done

ansible -m fetch -a "src=/etc/ceph/ceph.conf dest=/etc/ceph/ceph.conf.d" $monname -i $inventory_file
cp /etc/ceph/ceph.conf.d/$monname/etc/ceph/ceph.conf /etc/ceph/ceph.conf

ceph_client_key=/ceph-ansible-keys/`ls /ceph-ansible-keys/ | grep -v conf`/etc/ceph/ceph.client.admin.keyring
cp $ceph_client_key /etc/ceph/ceph.client.admin.keyring

#Health check
$script_dir/scripts/utils/check_cluster_status.py
exit_status=$?

exit $exit_status


#echo "Health check"
#$script_dir/scripts/utils/check_cluster_status.sh $inventory_file
#exit_status=$?
#
#if [ "$exit_status" -eq "0" ]; then
#	#copy client key to all clients
#	ceph_client_key=/ceph-ansible-keys/`ls /ceph-ansible-keys/ | grep -v conf`/etc/ceph/ceph.client.admin.keyring
#	ansible -m copy -a "src=$ceph_client_key dest=/etc/ceph/ceph.client.admin.keyring" clients -i $inventory_file 
#else
#	exit 1
#fi