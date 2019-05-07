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
#pip install -I urllib3
pip install -I requests
cd $archive_dir

#if cbt
	$script_dir/scripts/index_cbt.py -t $Test_ID -h $elasticsearch_host -p $elasticsearch_port -d
#else if cosbench
	#index_cosbench
#else if 
	#index_smallfile
#fi