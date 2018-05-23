#!/bin/bash

#get home directory 
HOME_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $HOME_DIR

#TODO for each job file update the script dir and change it to the user's install location

#TODO install jenkins version 110 discovered that jobs are not backwards compatible 
rpm -i https://pkg.jenkins.io/redhat/jenkins-2.110-1.1.noarch.rpm

#TODO maybe install elasticsearch and grafana, alter ask user if they want to install ES and grafana

#install pbench web server 




