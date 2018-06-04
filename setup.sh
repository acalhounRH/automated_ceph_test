#!/bin/bash

#TODO install ceph-linode and CBT-pbench-branch

master_node=false
agent_node=false
linode_install=false

while getopts ":ma" opt; do
  case ${opt} in
    m ) 
        master_node=true
      ;;
    a ) 
        agent_node=true
      ;;
    l )
        linode_install=true
      ;;
    \? ) echo "Usage:
              -m - setup a master automated_ceph_test node
              -a - setup a agent automated_ceph_test node
              -l - installing automated_ceph_test on linode

              master - ./setup.sh -m 
              agent - ./setup.sh -a 
              linode agent - .setup.sh -a -l"
      ;;
  esac
done

cd $HOME

if [ ! -d ceph-linode ] ; then
	git clone https://github.com/batrick/ceph-linode
fi

#git clone -b <branch> <remote_repo> # installing CBT version with pbench performance monitoring
if [ ! -d cbt ]; then
  git clone -b pbench-integration https://github.com/acalhounRH/cbt.git
fi 

yum install httpd -y

if [ -d perf-dept ]; then
  cd perf-dept
  git checkout master
	git remote update
	git rebase 
  cd sysadmin/Ansible
else
	git clone http://git.app.eng.bos.redhat.com/git/perf-dept.git
  cd perf-dept/sysadmin/Ansible
fi

ansible-playbook pbench-repo-install.yml -i localhost, -k

if [ $linode_install ]; then
	echo "******************* install pbench agent in linode"
	ansible -m shell -a "yum install yum-utils -y; yum-config-manager --disable pbench; yum install pbench-agent -y" -i localhost, -k 
  echo "*******************install pbench-fio and pdsh for CBT"
  ansible -m shell -a "yum install pbench-fio -y; yum install pdsh -y;" all -i localhost, -k 
else
	echo "******************* install pbench agent"
	ansible-playbook pbench-agent-internal-install.yml -i localhost, -k 
fi

yum install pbench-web-server

ln -sf /opt/pbench-web-server/html/static /var/www/html
ln -sf /var/lib/pbench-agent /var/www/html

systemctl start httpd

echo "browse to http://localhost/pbench-agent for pbench webservice" 

#install jenkins version 110 if master flag is used.
if [ $master_node ]; then
  rpm -i https://pkg.jenkins.io/redhat/jenkins-2.110-1.1.noarch.rpm
fi 
