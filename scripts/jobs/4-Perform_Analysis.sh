#!/bin/bash

script_dir=$HOME/automated_ceph_test
pip install -I urllib3
cd $archive_dir

#if cbt
	$script_dir/scripts/index_cbt.py -t $Test_ID -h $elasticsearch_host -p $elasticsearch_port -d 
#else if cosbench
	#index_cosbench
#else if 
	#index_smallfile
#fi