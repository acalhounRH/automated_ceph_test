#!/bin/bash -x

# replace with $script_dir/scripts/run-smallfile.sh

script_dir=$HOME/automated_ceph_test
mon_port=6789
mountpoint=/mnt/cephfs
NOTOK=1

# this subroutine installs software from github
# if it's a branch rather than master, you
# have to do a couple of extra steps

clone_branch() {
	cd
	git_url=$1
	echo $git_url | grep '/tree/'
	if [ $? = 0 ] ; then
		git_branch_name=`basename $git_url`
		git_branch_tree=`dirname $git_url`
		git_site=`dirname $git_branch_tree`
	else
		git_site=$git_url
	fi
	git_dirname=`basename $git_site`
	rm -rf $git_dirname
	git clone $git_site
	cd $git_dirname
	if [ -n "$git_branch_name" ] ; then
		git fetch $git_site $git_branch_name
		git checkout $git_branch_name
	fi
	rm -rf .git
	cd
	ansible -m synchronize -a "src=~/$git_dirname delete=yes dest=./" clients
}

hostname | grep -q linode.com
if [ $? = 0 ]; then
        inventory_file=$HOME/ceph-linode/ansible_inventory
else
        inventory_file=$script_dir/ansible_inventory
fi
export ANSIBLE_INVENTORY=$inventory_file

rm -rf $archive_dir
mkdir -v $archive_dir

ansible -m shell -a 'yum install -y rsync' clients || exit 1

clone_branch $cbt_url
clone_branch $smallfile_url

# CBT doesn't know where you put smallfile
# so it expects it to be in PATH
ln -svf ~/smallfile/smallfile_cli.py /usr/local/bin
ansible -m shell -a "ln -svf ~/smallfile/smallfile_remote.py /usr/local/bin/" clients

echo "$smallfile_settings" | tee $archive_dir/automated_test.yml

# get monitor IP address, we'll need that to mount Cephfs

mon_ip=`ansible -m shell -a 'echo {{ hostvars[groups["mons"][0]]["ansible_ssh_host"] }}' localhost | grep -v localhost`

# distribute client key to Cephfs clients in expected format

(rm -f /etc/ceph/cephfs.key && \
 awk '/==/{ print $NF }' /etc/ceph/ceph.client.admin.keyring > /etc/ceph/cephfs.key && \
 ansible -m copy -a 'src=/etc/ceph/cephfs.key dest=/etc/ceph/' clients) \
  || exit $NOTOK

# it's ok if unmounting fails because it's not already mounted

ansible -m shell -a "umount -v $mountpoint" clients

# if we can't mount Cephfs, bail out right away

ansible -m shell -a \
 "mkdir -pv $mountpoint && mount -v -t ceph -o name=admin,secretfile=/etc/ceph/cephfs.key $mon_ip:$mon_port:/ $mountpoint && mkdir -pv $mountpoint/smf" clients \
   || exit $NOTOK

# must mount cephfs from test driver as well

umount $mountpoint
(mkdir -pv $mountpoint && \
 mount -v -t ceph -o name=admin,secretfile=/etc/ceph/cephfs.key $mon_ip:$mon_port:/ $mountpoint && \
 mkdir -pv $mountpoint/smf ) \
 || exit $NOTOK

# run the test and save results in archive_dir

source /etc/profile.d/pbench-agent.sh
rm -rf $archive_dir/cbt_results
mkdir -pv $archive_dir/cbt_results
benchyaml=$archive_dir/benchmark.yaml
echo "$cbt_smallfile_settings" > $benchyaml
# need to get indentation right for YAML, next cmd copies indentation
grep 'operation:' $benchyaml | sed 's#operation:.*$#top: /mnt/cephfs/smf#' >> $benchyaml
$script_dir/scripts/utils/addhost_to_jobfile.sh $archive_dir/benchmark.yaml $ANSIBLE_INVENTORY
echo "################ CBT YAML input ################"
cat $archive_dir/benchmark.yaml
# CBT uses localhost in "head" role so we need password-less 
# ssh access to localhost, this command fixes known_hosts to allow it
ssh -o StrictHostKeyChecking=no localhost pwd

pbench-user-benchmark -- python ~/cbt/cbt.py -a $archive_dir/cbt_results $archive_dir/benchmark.yaml
rc=$?
umount -v $mountpoint
rm -fv /etc/ceph/cephfs.key smf-clients.list

exit $rc
