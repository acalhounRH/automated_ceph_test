#!/bin/bash +x

script_dir=$HOME/automated_ceph_test/

host=`grep $agent_name ~/agent_list |awk -F'=' '{print $2}'`

if [ -Z $host ]; then
	echo "$host is not in agent_list"
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
    `python2 ./scripts/remove-linode-agent.py`
else 
	#issue ssh remote command to destory swam-client
	ssh $host " pkill -f swarm-client"
fi 
#issue pkill command, command will kill command with full process name containing host
#SIGTERM
pkill -f $host

#remove host from agent_list, create back up just in case
sed -i.bak "/$agent_name/d" ~/agent_list

#remove host from agent_port_range file, create back up just in case
sed -i.bak "/$agent_name/d"  ~/agent_port_range
