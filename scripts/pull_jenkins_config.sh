#!/usr/bin/bash

  echo "Pulling jobs:"
for i in `ls /var/lib/jenkins/jobs/`; do 
	echo $i

  mkdir -p /automated_ceph_test/jenkins_config/jobs/$i/
  cp  -r /var/lib/jenkins/jobs/$i/config.xml ~/automated_ceph_test/jenkins_config/jobs/$i/
done

  cp /var/lib/jenkins/config.xml ~/automated_ceph_test/jenkins_config/config.xml
  sed -i '/<useSecurity>/,/<\/useSecurity>/s/true/false/' ~/automated_ceph_test/jenkins_config/config.xml


