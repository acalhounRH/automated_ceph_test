#!/usr/bin/bash

inventory_file=$1

host=`hostname`

new_host="
        Host $host
        User root
        UserKnownHostsFile /dev/null
        StrictHostKeyChecking no
        "
        
for cur_host in `ansible --list-hosts all -i $inventory_file | grep -v hosts`; do
	ping $cur_host -c 1 > /dev/null 2>&1
    exit_status=`echo $?`
    if [ "$exit_status" -gt "0" ]; then
    		host=`cat $inventory_file | grep $cur_host | awk {'print $2'} | sed 's/.*=//'`		
	echo $host
    elif [ "$exit_status" -eq "0" ]; then
    		host=$cur_host
	echo $host
	fi
	
	ssh $host "ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N \"\" ; echo \"$new_host\" >> $HOME/.ssh/config " ;
    pubkey=`ssh $host "cat ~/.ssh/id_rsa.pub"`
    echo $pubkey>> ~/.ssh/authorized_keys
done

echo "setup round trip between host and control node"
