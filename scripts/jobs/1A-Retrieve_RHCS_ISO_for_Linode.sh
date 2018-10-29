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

# lookup agent IP using agent name

agenthostname=`cat ~/agent_list | grep -i $agentname | cut -d "=" -f 2`

# pull iso, assumption is that wget on internal network is fast

rm -rf iso_holder
mkdir iso_holder
cd iso_holder

if [[ $ceph_iso_file =~ "RHCEPH-*-x86_64-dvd.iso" ]]; then
    echo "**************$ceph_iso_file"
    sudo wget -r -nd --no-parent -A "$ceph_iso_file" $ceph_iso_path &> /dev/null
    new_ceph_iso_file="$(ls)"
else
    sudo wget $ceph_iso_path/$ceph_iso_file &> /dev/null
    new_ceph_iso_file=$ceph_iso_file
fi
if [ ! -f $new_ceph_iso_file ] ; then 
    echo "FAILED to fetch .iso file"
    exit 1
fi
ls

# clear out linode agent ceph-ansible staging area

ssh $agenthostname " 
	hostname
	cd ~/automated_ceph_test/staging_area
	mkdir -pv rhcs_latest rhcs_old || exit 1
	mv -v rhcs_latest/* rhcs_old/
	ls -l rhcs_old/ || echo ''
" || exit 1 

# copy iso to agent if necessary

echo "###################### $new_ceph_iso_file $agenthostname"
scp $new_ceph_iso_file $agenthostname:~/automated_ceph_test/staging_area/rhcs_latest || exit 1

# remove local dir

cd ../
rm -rf iso_holder
