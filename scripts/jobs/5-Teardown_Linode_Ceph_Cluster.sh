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

echo "to suspend teardown indefinitely: touch /tmp/suspend-teardown"
echo "to resume teardown:               rm /tmp/suspend-teardown"
echo "to cause immediate teardown:      touch /tmp/teardown-now"
echo "you must login to the remote agent from jenkins master to use this"
echo "teardown script will check for these files every 60 seconds"
echo ""

(( teardown_sec = $teardown_delay_minutes * 60 ))
while [ $teardown_sec -gt 0 ] ; do
    if [ -f /tmp/teardown-now ] ; then
        echo "saw /tmp/teardown-now, starting tear-down now"
        rm -fv /tmp/teardown-now
        break
    fi
    sleep 60
    (( teardown_sec = $teardown_sec - 60 ))
    echo "waiting $teardown_sec seconds before tear-down"
done

# this feature enables script debugging for pipelines
# you can't debug scripts once linodes are destroyed

while [ -f /tmp/suspend-teardown ] ; do
    echo "waiting for /tmp/suspend-teardown file to be removed..."
    sleep 60
done

# first tear down Ceph on this agent 
# so we don't have dangling mountpoints, etc

umount -a -ff -t ceph
yum remove -y ceph-common ceph-fuse librados2 ceph-ansible
leftovers=`rpm -qa | awk '/ceph/||/librados/||/librbd/' | wc -l` 
if [ $leftovers -gt 0 ] ; then
    echo 'not all Ceph RPMS removed!'
    rpm -qa | awk '/ceph/||/librados/||/librbd/'
fi

# now tear down the linode cluster

cd $HOME/ceph-linode/
virtualenv-2 linode-env && source linode-env/bin/activate && pip install linode-python
export LINODE_API_KEY=$Linode_API_Key
python ./linode-destroy.py || exit 1
echo "LINODE_GROUP = `cat ~/ceph-linode/LINODE_GROUP`"
rm -fv ~/ceph-linode/LINODE_GROUP
