#!/bin/bash +x


for agentname_hostname in `cat ~/agent_list`; then
do 
	agentname=`echo agentname_hostname | awk -f= '{print $1}'`
	agent_hostname=`echo agentname_hostname | awk -f= '{print $2}'`
	
	jenkins_master_port=`cat ~/agent_port_range | grep $agentname | awk -F= '{print $2}' | awk -F- '{print $1}'`
	jenkins_client_port=$($jenkins_master_port+3)
	elasticsearch_port=$($jenkins_master_port+6)
	
	# need to store active ports 
(( port1 = 20000 + $jenkins_masater_port ))
(( port2 = 30000 + $jenkins_client_port ))
(( port3 = 40000 + $elasticsearch_port ))
echo "STARTING AUTOSSH"
autossh -M $port1 -f -N $agent_hostname -R 8080:localhost:8080 -C 
echo "autossh -M $port1 -f -N $agent_hostname -R 8080:localhost:8080 -C"
autossh -M $port2 -f -N $agent_hostname -R 8081:localhost:8081 -C
echo "autossh -M $port2 -f -N $jenkins_agent -R 8081:localhost:8081 -C"
autossh -M $port3 -f -N $agent_hostname -R 9200:10.16.31.52:9200 -C
echo "autossh -M $port3 -f -N $agent_hostname -R 9200:10.16.31.52:9200 -C"
done

