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

script_dir=$HOME/automated_ceph_test

if [ "$linode_cluster" == "true" ]; then
	inventory_file=$HOME/ceph-linode/ansible_inventory
else
	inventory_file=$script_dir/ansible_inventory
fi

source /etc/profile.d/pbench-agent.sh
mkdir -p $HOME/cbt/jenkins_jobfiles/
jobfiles_dir=$HOME/cbt/jenkins_jobfiles/
echo "$settings" > $jobfiles_dir/automated_test.yml

$script_dir/scripts/utils/addhost_to_jobfile.sh $jobfiles_dir/automated_test.yml $inventory_file

echo "################Jenkins Job File################"
cat $jobfiles_dir/automated_test.yml

sudo mkdir -m 777 $archive_dir
$HOME/cbt/cbt.py $jobfiles_dir/automated_test.yml -a $archive_dir

#echo "role_to_hostnames [ " > $archive_dir/results/ansible_facts.json
#ansible all -m setup -i $inventory_file | sed -s 's/ | SUCCESS => /"&/' | sed -s 's/ | SUCCESS => /": /' | sed -s 's/},/}/' | sed -s 's/}/},/' >> $archive_dir/results/ansible_facts.json
#echo "]" >> $archive_dir/results/ansible_facts.json

