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

copr_repo_url="https://copr.fedorainfracloud.org/coprs/ndokos/pbench/repo/epel-7/ndokos-pbench-epel-7.repo"
epel_repo_rpm_url="https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm"
NOTOK=1

register_tool() {
    pbench-register-tool --name=$1 --remote=$2 default -- --interval=$3 || exit $NOTOK
}

script_dir=$HOME/automated_ceph_test

#set inventory file
hostname | grep linode.com
if [ $? = 0 ]; then
    export linode_cluster=true
    echo "setting up for linode"
    inventory_file=$HOME/ceph-linode/ansible_inventory
else
    inventory_file=$script_dir/ansible_inventory
fi 

#Based on user input register pbench monitoring tools
function register_tools {
    hst=$1
    if [ "$sar" = "true" ]; then
        register_tool sar $hst $sar_interval
    fi
    if [ "$iostat" = "true" ]; then
        register_tool iostat $hst $iostat_interval
    fi
    if [ "$mpstat" = "true" ]; then
        register_tool mpstat $hst $mpstat_interval
    fi
    if [ "$pidstat" = "true" ]; then
        register_tool pidstat $hst $pidstat_interval
    fi
    if [ "$proc_vmstat" = "true" ]; then 
        register_tool proc-vmstat $hst $proc_vmstat_interval
    fi
    if [ "$proc_interrupts" = "true" ]; then
        register_tool proc-interrupts $hst $proc_interrupts_interval
    fi
    if [ "$turbostat" = "true" ]; then
        if [ "$linode_cluster" = "true" ] ; then
            echo "you cannot run turbostat within linode VM"
        else
            register_tool turbostat $hst $turbostat_interval
        fi
    fi
}


if [ "$linode_cluster" == "true" ]; then
    echo "copy linode inventory"
    cp $HOME/ceph-linode/ansible_inventory $inventory_file
fi

echo "$service_inventory" >> $inventory_file

#Setup and install pbench on all linode host
cat $inventory_file


yum remove -y pbench-fio pbench-agent pbench-sysstat
rm -rf /var/lib/pbench-agent
yum install -y $epel_repo_rpm_url
(yum install -y yum-utils wget && \
 yum-config-manager --enable epel && \
 (cd /etc/yum.repos.d && wget $copr_repo_url) && \
 yum install pbench-fio pbench-agent pbench-sysstat pdsh -y) \
  || exit $NOTOK

# now do same thing on all remote hosts

export ANSIBLE_INVENTORY=$inventory_file
ansible -m yum -a "name=$epel_repo_rpm_url" all
(ansible -m yum -a "name=pbench-fio,pbench-agent,pbench-sysstat state=absent" all && \
 ansible -m shell -a "rm -rf /var/lib/pbench-agent" all && \
 ansible -m yum -a "name=wget,yum-utils" all && \
 ansible -m shell -a "cd /etc/yum.repos.d; wget $copr_repo_url" all && \
 ansible -m shell -a "yum-config-manager --enable epel" all && \
 ansible -m yum -a "name=pbench-fio,pdsh,pbench-agent,pbench-sysstat" all) \
  || exit $NOTOK
 

echo "******************* registering tools:"

source /etc/profile.d/pbench-agent.sh
ansible --list-host all | grep -v hosts | grep -v ':' > /tmp/host.list

for i in `cat /tmp/host.list`
    do
        echo "setting up host $i"
        if [ "$linode_cluster" = "true" ]; then
            echo "Registering tools on Linode host"
            IP_address=`cat $inventory_file | grep $i | awk {'print $2'} | sed 's/.*=//'`
            register_tools $IP_address || exit $NOTOK
        else
            echo "Registering tools on pre-existing host"
            register_tools $i || exit $NOTOK
        fi
done

