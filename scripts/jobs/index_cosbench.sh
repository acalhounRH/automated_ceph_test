#!/usr/bin/bash -x


#setup tools on Control host
ssh root@$cosbench_controller "
	#install git 
	if [ $? -eq 0 ] ; then
		echo 'git installed'
	else
		yum install git -y
	fi
	
	#change dir to home and check if automated ceph test is installed
	#if it is pull latest else git clone
	cd ~
	if [ -d ~/automated_ceph_test ] ; then
		cd ~/automated_ceph_test
		git pull 
	else
		git clone https://github.com/acalhounRH/automated_ceph_test
		#install supporting python packages
		pip install pyyaml
		pip install elasticsearch 
		pip install urllib3==1.23
		pip install statistics
		pip install xmltodict
	fi 	

	"
#run index_cosbench
ssh root@$cosbench_controller "
	#check that archive dir is there
	if [ -d $cosbench_archive ] ; then
		cd $cosbench_archive
		~/automated_ceph_test/scripts/index_cosbench.py -t $Test_ID -h $elasticsearch_host -p $elasticsearch_port -w \"$workload_list\"
	else
		echo 'cosbench archive does not exist'
	fi
	"