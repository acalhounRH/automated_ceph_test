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

script_dir=$HOME/automated_ceph_test/
NOTOK=1

# ensure autossh is installed before doing anything
which autossh || exit $NOTOK

lowercase_agent_name=`echo "$agent_name" | awk '{print tolower($0)}'`

if [[ `grep "^${lowercase_agent_name}=" ~/agent_list` ]]; then
	echo 'Agent name already in use, aborting!'
    exit $NOTOK
fi
if [[ `grep "=${agent_host}" ~/agent_list` ]] ; then 
    echo 'Agent host already in use, aborting'
    exit $NOTOK
fi
#check if agent host have was specified, if it was the assumption is that its an internal host.
if [ ! -z "$agent_host" ]; then
	#assumption is that ssh keys have been copied and placed on agent and all cluster servers
	jenkins_agent=$agent_host
    setup_cmd="setup.sh -a" #set the setup_cmd to agent setup
    echo "*****************************"
#	new_host="
#		Host $jenkins_agent
#	  		User root
#	  		StrictHostKeyChecking no
#		"	
#	echo "$new_host" >> $HOME/.ssh/config
else
	#assumption, since the user did not specify a hostname we will assume this is a linode agent.
	setup_cmd="setup.sh -a -l" #set the setup_cmd to linode agent setup
	cd $script_dir 
    pwd
	virtualenv linode-env && source linode-env/bin/activate && pip install linode-python
    ###:TODO need to add a check that linode_api_key is not null
	export LINODE_API_KEY=$Linode_API_key
	jenkins_agent=`python2 ./scripts/utils/create_linode_agent.py`
	
	if [ -Z $jenkins_agent ]; then
		echo "Failed to retrieve agent hostname"
		exit $NOTOK
	fi

	if [ "$jenkins_agent" == "jenkins agent already created" ]; then
    	echo "Linode Jenkins agent already exists!"
		exit $NOTOK
	fi
	echo "*****************************"
fi

echo "$lowercase_agent_name=$jenkins_agent" >> ~/agent_list

new_host="
	Host $jenkins_agent
	User root
	UserKnownHostsFile /dev/null
	StrictHostKeyChecking no
	"

echo "$new_host" >> $HOME/.ssh/config


# automatic port ranges, 0-2, 3-5, 6-8, etc
#only need three ports to forward, 1 jenkings master, 2 jenkins client, 3 elasticsearch 
jenkins_master_port=0
jenkins_client_port=2
elasticsearch_port=4

for i in {0..101}; do #allows for about 100 agents, dont expect this to happen.
	
    
	if [ "$i" -eq "101" ]; then
    	echo "No more ports available"
        exit 1
    fi
    
	port_range="${jenkins_master_port}-${elasticsearch_port}"
	#check if current range is not used, if so use specified port ranges and add them to file
    #then break out of loop.
    
	if [[ ! `grep $port_range ~/agent_port_range` ]]; then
    	echo "$lowercase_agent_name=$port_range" >> ~/agent_port_range
    	break
    else
		#increment all three ports by three
		jenkins_master_port=$((jenkins_master_port+3))
		jenkins_client_port=$((jenkins_client_port+3))
		elasticsearch_port=$((elasticsearch_port+3))
	fi
done

# need to store active ports 
(( port1 = 20000 + $jenkins_master_port ))
(( port2 = 30000 + $jenkins_client_port ))
(( port3 = 40000 + $elasticsearch_port ))
echo "STARTING AUTOSSH"
autossh -M $port1 -f -N $jenkins_agent -R 8080:localhost:8080 -C 
echo "autossh -M $port1 -f -N $jenkins_agent -R 8080:localhost:8080 -C"
autossh -M $port2 -f -N $jenkins_agent -R 8081:localhost:8081 -C
echo "autossh -M $port2 -f -N $jenkins_agent -R 8081:localhost:8081 -C"
autossh -M $port3 -f -N $jenkins_agent -R 9200:10.16.31.52:9200 -C
echo "autossh -M $port3 -f -N $jenkins_agent -R 9200:10.16.31.52:9200 -C"
 
j_host="
	Host $jenkins_agent
		User root
		StrictHostKeyChecking no
		"

#setup ssh loopback to agent host
ssh $jenkins_agent "
    
    echo \"$j_host\" >> ~/.ssh/config
    ssh-keygen -f ~/.ssh/id_rsa -t rsa -N \"\"
    ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub
    sync
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    sync
    ssh $jenkins_agent \"echo \\"##############################\\"; date\"
    "

#install automated ceph test download swarm-client jar
ssh $jenkins_agent "
	yum install git -y
    yum install wget -y
    yum install patch -y
	cd
	git clone https://github.com/acalhounRH/automated_ceph_test
    eval ~/automated_ceph_test/setup.sh -a -l
    # remove when updated to 3.1, needed on 3.0
    patch ceph-linode/launch.sh automated_ceph_test/scripts/patches/ceph-linode.patch
	yum install java -y
    if [ ! -f swarm-client-3.9.jar ]; then
    	wget https://repo.jenkins-ci.org/releases/org/jenkins-ci/plugins/swarm-client/3.9/swarm-client-3.9.jar
    fi   
    "
#start a background headless jenkins swam agent
#DO NOT CHANGE FROM localhost
ssh $jenkins_agent "nohup java -jar swarm-client-3.9.jar -master http://localhost:8080 -disableClientsUniqueId -name $lowercase_agent_name -labels $lowercase_agent_name -executors 5 & " &
