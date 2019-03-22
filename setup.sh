#!/bin/bash +x

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
	#git clone https://github.com/batrick/ceph-linode
	git clone -b update_to_linode_APIv4 https://github.com/acalhounRH/ceph-linode.git
fi

#git clone -b <branch> <remote_repo> # installing CBT version with pbench performance monitoring
if [ ! -d cbt ]; then
 	git clone -b pbench-integration https://github.com/acalhounRH/cbt.git
fi 

if [ ! -d smallfile ]; then
	git clone https://github.com/bengland2/smallfile.git
fi 

epel_status=`rpm -qa | grep epel`

if [ "$epel_status" != "0" ]; then
  wget http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
  rpm -ivh epel-release-latest-7.noarch.rpm
fi 

sed -i 's/enabled=0/enabled=1/g' /etc/yum.repos.d/epel.repo
yum install python-virtualenv -y
yum install python-pip -y
pip install pip -U
pip install pyyaml
pip install elasticsearch 
#pip install urllib3==1.23
pip install statistics
pip install xmltodict
pip install linode_api4

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
wget -O /etc/yum.repos.d/pbench.repo http://pbench.perf.lab.eng.bos.redhat.com/repo/production/yum.repos.d/pbench.repo /etc/yum.repos.d/

#if [ "$linode_install" == "true" ]; then
#	echo "******************* install pbench agent in linode"
#	yum install yum-utils -y;
#  yum-config-manager --disable pbench;
#  yum install pbench-agent -y
#else
#	echo "******************* install pbench agent"
#	yum install pbench-agent-internal -y
#fi

#install pbench-agent
cd /etc/yum.repos.d
wget https://copr.fedorainfracloud.org/coprs/ndokos/pbench/repo/epel-7/ndokos-pbench-epel-7.repo; 
yum install pbench-agent -y

#install pbench web server
yum install httpd npm -y
yum install pbench-web-server -y

sed -i 's/enabled=1/enabled=0/g' /etc/yum.repos.d/epel.repo

ln -sf /opt/pbench-web-server/html/static /var/www/html
ln -sf /var/lib/pbench-agent /var/www/html

systemctl start httpd

echo "browse to http://localhost/pbench-agent for pbench webservice" 

#install jenkins version 110 if master flag is used.
if [ "$master_node" == "true" ]; then
  #rpm -i https://pkg.jenkins.io/redhat/jenkins-2.110-1.1.noarch.rpm
  wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat/jenkins.repo
  rpm --import https://pkg.jenkins.io/redhat/jenkins.io.key
  yum install java -y
  yum install jenkins -y
fi 
