#!/usr/bin/bash

for i in `ls /var/lib/jenkins/jobs/`; do 
	echo $i 
	mkdir /automated_ceph_test/jenkins_config/jobs/$i
	cp /var/lib/jenkins/jobs/$i/config.xml /automated_ceph_test/jenkins_config/jobs/$i/
done
