#!/bin/bash -x

# replace with $script_dir/scripts/run-smallfile.sh

script_dir=$HOME/automated_ceph_test
mon_port=6789
mountpoint=/mnt/cephfs
NOTOK=1

hostname | grep -q linode.com
if [ $? = 0 ]; then
        inventory_file=$HOME/ceph-linode/ansible_inventory
else
        inventory_file=$script_dir/ansible_inventory
fi
export ANSIBLE_INVENTORY=$inventory_file

mkdir -v $archive_dir

# prepare smallfile parameters in a YAML file

echo "$smallfile_settings" | tee $archive_dir/automated_test.yml

# ensure smallfile up to date on all client machines

smf_git_repo='https://github.com/distributed-system-analysis/smallfile'
ansible -m shell -a "yum install -y git ; git clone $smf_git_repo || (cd smallfile ; git pull)" clients

# get list of client hosts to feed to smallfile

rm -fv smf-clients.list
ln -sv $archive_dir/smf-clients.list .
ansible -m shell -a hostname clients 2>&1 | \
  grep -v SUCCESS | tee $archive_dir/smf-clients.list
  
# get monitor IP address, we'll need that to mount Cephfs

mon_ip=`ansible -m shell -a 'echo {{ hostvars[groups["mons"][0]]["ansible_ssh_host"] }}' localhost | grep -v localhost`

# fetch and distribute client.admin key to Cephfs clients in expected format

(scp $mon_ip:/etc/ceph/ceph.client.admin.keyring /tmp/ceph.client.admin.keyring && \
 awk '/==/{ print $NF }' /tmp/ceph.client.admin.keyring > /tmp/cephfs.key && \
 ansible -m copy -a 'src=/tmp/cephfs.key dest=/etc/' clients) \
  || exit $NOTOK

# it's ok if unmounting fails because it's not already mounted

ansible -m shell -a "umount -v $mountpoint" clients

# if we can't mount Cephfs, bail out right away

ansible -m shell -a \
 "mkdir -pv $mountpoint && mkdir -pv $mountpoint/smf && mount -v -t ceph -o name=admin,secretfile=/etc/cephfs.key $mon_ip:$mon_port:/ $mountpoint && mkdir -pv $mountpoint/smf" clients \
   || exit $NOTOK

# must mount cephfs from test driver as well

umount $mountpoint
(mkdir -pv $mountpoint && \
 mount -v -t ceph -o name=admin,secretfile=/tmp/cephfs.key $mon_ip:$mon_port:/ $mountpoint && \
 mkdir -pv $mountpoint/smf ) \
 || exit $NOTOK

# run the test and save results in archive_dir

source /etc/profile.d/pbench-agent.sh
pbench-user-benchmark -- python $HOME/smallfile/smallfile_cli.py \
  --yaml-input-file $archive_dir/automated_test.yml 2>&1 | \
  tee $archive_dir/smf.log
# since this is the agent, don't leave Cephfs mounted here 
# because servers will go away
umount -v $mountpoint
rm -fv /tmp/cephfs.key smf-clients.list 
# if smallfile fails, then next command fails and so job fails
mv -v result.json $archive_dir/
