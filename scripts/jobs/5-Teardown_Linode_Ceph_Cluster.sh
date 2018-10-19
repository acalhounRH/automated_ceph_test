#!/bin/bash

# this script implements the Jenkins job by the same name,
# just call it in the "Execute shell" field 
# in the job configuration
# because bash doesn't throw exceptions, 
# the script doesn't stop automatically because of a 
# fatal error, we have to check for errors and exit 
# with an error status if one is seen, 
# Jenkins will stop the pipeline immediately,
# this makes troubleshooting a pipeline much easier for the user

(( teardown_sec = $teardown_delay_minutes * 60 ))
echo "waiting $teardown_sec seconds before tear-down"
sleep $teardown_sec

while [ -f /tmp/suspend_teardown ] ; do
	echo "waiting for /tmp/suspend_teardown file to be removed..."
	sleep 60
done

cd $HOME/ceph-linode/
virtualenv-2 linode-env && source linode-env/bin/activate && pip install linode-python
export LINODE_API_KEY=$Linode_API_Key
python ./linode-destroy.py
