#!/usr/bin/bash

inventory_file=$1

ARRAY=()
for host in `ansible --list-hosts $i -i $inventory_file | grep -v hosts`; do
	ping $j -c 1 > /dev/null 2>&1
    exit_status=`echo $?`
    if [ "$exit_status" -gt "0" ]; then
    		host=`cat $inventory_file | grep $host | awk {'print $2'} | sed 's/.*=//'`		
	echo $host
    elif [ "$exit_status" -eq "0" ]; then
    		host=$j
	echo $host
	fi
	ARRAY+=($host)
done

host=`hostname`

new_host="
        Host $host
        User root
        UserKnownHostsFile /dev/null
        StrictHostKeyChecking no
        "

for i in `cat tmp`; do
        ssh $i "ssh-keygen -t rsa -q -N \"\" ; echo \"$new_host\" >> $HOME/.ssh/config " ;
        pubkey=`ssh $i "cat ~/.ssh/id_rsa.pub"`
        echo $pubkey>> ~/.ssh/authorized_keys
done

echo "setup round trip between host and control node"
#for i in `cat tmp`; do
#        ssh $i "echo \"$new_host\" >> $HOME/.ssh/config"
#        pubkey=`ssh $i "cat ~/.ssh/id_rsa.pub"`
#        echo $pubkey>> ~/.ssh/authorized_keys
#done
