#!/bin/bash -x

script_dir=$HOME/automated_ceph_test
mon_port=6789
mountpoint=/mnt/cephfs
NOTOK=1
numpy_pkg_name='python2-numpy'

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

ansible -m shell -a 'hostname -s' clients | grep -v SUCCESS > /tmp/h.tmp
for h in `cat /tmp/h.tmp` ; do hostlist="$hostlist $h" ; done
csv_hostlist=`echo $hostlist | sed 's/ /,/g'`

rm -rf $archive_dir
mkdir -v $archive_dir

# must have rsync installed everywhere for ansible synchronize module
# used by clone_branch function

ansible -m shell -a 'yum install -y rsync' clients || exit 1

clone_branch $fs_drift_url

# fs-drift.py doesn't know where you put it so it expects -remote.py to be in PATH

ansible -m shell -a "ln -svf ~/fs-drift/fs-drift-remote.py /usr/local/bin/" clients

# fs-drift.py expects python numpy module

(yum install -y $numpy_pkg_name && \
 ansible -m shell -a "yum install -y $numpy_pkg_name" all ) \
 || exit $NOTOK

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
 "mkdir -pv $mountpoint && mount -v -t ceph -o name=admin,secretfile=/etc/ceph/cephfs.key $mon_ip:$mon_port:/ $mountpoint && mkdir -pv $mountpoint/fs-drift" clients \
   || exit $NOTOK

# must mount cephfs from test driver as well

umount $mountpoint
(mkdir -pv $mountpoint && \
 mount -v -t ceph -o name=admin,secretfile=/etc/ceph/cephfs.key $mon_ip:$mon_port:/ $mountpoint && \
 mkdir -pv $mountpoint/fs-drift ) \
 || exit $NOTOK

# run the test and save results in archive_dir

source /etc/profile.d/pbench-agent.sh
resultdir=$archive_dir/fs-drift-results
mkdir -pv $resultdir

# CBT uses localhost in "head" role so we need password-less 
# ssh access to localhost, this command fixes known_hosts to allow it

ssh -o StrictHostKeyChecking=no localhost pwd

# save workload table where workers can read it

workload_table_fn=$mountpoint/fs-drift/workload_table.csv
echo "$workload_table" > $workload_table_fn

# remove any old log files so we get just what happened on this run

rm -f /var/tmp/fsd.*.log
ansible -m shell -a 'rm -f /var/tmp/fsd.*.log' clients

cmd="pbench-user-benchmark -- \
  python ~/fs-drift/fs-drift.py \
    --output-json $resultdir/fsd.json \
    --top $mountpoint/fs-drift \
    --response-times Y \
    --host-set $csv_hostlist \
    --workload-table $workload_table_fn \
    $fs_drift_parameters"
echo $cmd | tee $resultdir/fs-drift.cmd
eval "$cmd" 2>&1 | tee $resultdir/fs-drift.log
rc=$?
cp $mountpoint/fs-drift/network-shared/host*thrd*rsptimes.csv $resultdir/
cp $mountpoint/fs-drift/network-shared/counters.*.json $resultdir/
umount -v $mountpoint
rm -fv /etc/ceph/cephfs.key
ls $resultdir
exit $rc
