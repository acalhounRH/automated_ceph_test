#!/usr/bin/bash +x

# this script implements the Jenkins job by the same name,
# just call it in the "Execute shell" field 
# in the job configuration
# because bash doesn't throw exceptions, 
# the script doesn't stop automatically because of a 
# fatal error, we have to check for errors and exit 
# with an error status if one is seen, 
# Jenkins will stop the pipeline immediately,
# this makes troubleshooting a pipeline much easier for the user

echo "test test test"
systemctl stop firewalld 
systemctl stop iptables
script_dir=$HOME/automated_ceph_test
inventory_file=$HOME/ceph-linode/ansible_inventory

sudo yum remove ceph-ansible -y
rm -rf /usr/share/ceph-ansible

cd $script_dir/staging_area/rhcs_latest/
new_ceph_iso_file="$(ls)"

sudo rm -rf /ceph-ansible-keys
sudo mkdir -m0777 /ceph-ansible-keys

#mount ISO and create rhcs yum repo file 
sudo cp $script_dir/staging_area/repo_files/rhcs.repo /etc/yum.repos.d/
sudo mkdir -p /mnt/rhcs_latest/
sudo umount /mnt/rhcs_latest/
sudo mount $script_dir/staging_area/rhcs_latest/RHCEPH* /mnt/rhcs_latest/
sudo yum clean all


#install ceph-ansible
sudo yum install ceph-ansible -y

sudo sed -i 's/gpgcheck=1/gpgcheck=0/g' /usr/share/ceph-ansible/roles/ceph-common/templates/redhat_storage_repo.j2

mkdir -p $script_dir/staging_area/tmp
#setup all.yml
echo "$ceph_ansible_all_config" > $script_dir/staging_area/tmp/all.yml
sed -i "s/<ceph_iso_file>/$new_ceph_iso_file/g" $script_dir/staging_area/tmp/all.yml
sudo cp $script_dir/staging_area/tmp/all.yml /usr/share/ceph-ansible/group_vars/all.yml


#setup osd.yml
echo "$ceph_ansible_osds_config" > $script_dir/staging_area/tmp/osds.yml
sudo cp $script_dir/staging_area/tmp/osds.yml /usr/share/ceph-ansible/group_vars/osds.yml


#copy site.yml
sudo cp /usr/share/ceph-ansible/site.yml.sample /usr/share/ceph-ansible/site.yml


#Start Ceph-linode deployment
cd $HOME/ceph-linode
echo "$Linode_Cluster_Configuration" > cluster.json
virtualenv-2 linode-env && source linode-env/bin/activate && pip install linode-python
export LINODE_API_KEY=$Linode_API_KEY

ANSIBLE_STRATEGY=debug; /bin/bash +x ./launch.sh --ceph-ansible /usr/share/ceph-ansible
#sudo ansible -i ansible_inventory -m shell -a "ceph -s" mon-000

sleep 30
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