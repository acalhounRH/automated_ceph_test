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

script_dir=$HOME/automated_ceph_test/

# make sure you only match exactly that agent name
host=`grep "^${agent_name}=" ~/agent_list |awk -F'=' '{print $2}'`

if [ -z $host ]; then
	echo "host for $agent_name is not in agent_list"
    exit 1
fi

#if linode.com in host 
if [[ $host == *"linode.com"* ]]; then
  	echo "It's there!"
	#destroy linode vm
	cd $script_dir 
    pwd
	virtualenv linode-env && source linode-env/bin/activate && pip install linode-python
    ###:TODO need to add a check that linode_api_key is not null
    if [ ! -z $Linode_API_key ]; then
		export LINODE_API_KEY=$Linode_API_key
    else
    	echo "No linode API given, aborting!"
        exit 1
    fi
    `python2 ./scripts/utils/remove_linode_agent.py`
else 
	#issue ssh remote command to destory swam-client
	ssh $host " pkill -f -- swarm-client"
fi 
#issue pkill command, command will kill command with full process name containing host
#make sure you match only that one
#SIGTERM
pkill -f -- "-N $host "

#remove host from agent_list, create back up just in case
sed -i.bak "/^$agent_name=/d" ~/agent_list

#remove host from agent_port_range file, create back up just in case
sed -i.bak "/^$agent_name=/d"  ~/agent_port_range
