#!/usr/bin/bash

  echo "Pulling jobs:"
for i in `ls /var/lib/jenkins/jobs/`; do 
	echo $i 
done

	cp  -r /var/lib/jenkins/jobs/ /automated_ceph_test/jenkins_config/jobs/


