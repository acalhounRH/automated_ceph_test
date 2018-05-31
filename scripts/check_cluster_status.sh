#!/usr/bin/bash

exit_status=0
time_out=0
inventory_file=$1
#inventory_file=/automated_ceph_test/ceph-linode/ansible_inventory

while [ "$exit_status" -eq "0" ]; do
	ansible -m ping all -i $inventory_file | grep UNREACHABLE
	exit_status=`echo $?`

	if [ "$time_out" -eq "60" ]; then
		exit 1
	fi

	time_out=$((time_out+1))
	sleep 5
done
	echo "nodes up"
#ceph_status=`ansible -m shell -a "ceph -s" mon-000 -i $inventory_file | grep health: | awk {'print $2'}`
ceph_status=`ansible -m shell -a "ceph -s" mons -i /automated_ceph_test/ansible_inventory | grep health: | awk {'print $2'}`
if [[ $ceph_status = *"HEALTH_OK"* ]]; then
	echo "Health: $ceph_status"
	exit 0
else 
	ansible -m shell -a "ceph -s" mons -i $inventory_file
	exit 1 
fi
