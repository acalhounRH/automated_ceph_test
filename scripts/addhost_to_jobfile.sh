#!/usr/bin/bash

job_file=$1
headset=false
inventory_file=/automated_ceph_test/ceph-linode/ansible_inventory

ceph_ary=(mons osds mgrs mdss clients)
for i in "${ceph_ary[@]}"; do
	 for j in `ansible --list-hosts $i -i $inventory_file | grep -v hosts`; do

		ping $j -c 1 > /dev/null 2>&1
                exit_status=`echo $?`
                if [ "$exit_status" -gt "0" ]; then
                		host=`cat $inventory_file | grep $j | awk {'print $2'} | sed 's/.*=//'`
				echo $host
                elif [ "$exit_status" -eq "0" ]; then
                		host=$j
				echo $host
                else
                        echo "Unable to connect to $j"
				echo $host
                fi

		if [[ "$i" =~ .*osd.* ]]; then
			osdhost_list="$osdhost_list\"$host\","
		elif [[ "$i" =~ .*mons.* ]]; then
			monhost_list="$monhost_list\"$host\","
		elif [[ "$i" =~ .*clients.* ]]; then
			if [[ $headset == false ]] ; then
				headnode=$host
				headset=true
			fi
			clienthost_list="$clienthost_list\"$host\","
		fi 
	done
done

sed -i "s/<OSD_LIST>/$osdhost_list/g" $job_file
sed -i "s/<MON_LIST>/$monhost_list/g" $job_file
sed -i "s/<CLI_LIST>/$clienthost_list/g" $job_file
sed -i "s/<test_host>/$headnode/g" $job_file
