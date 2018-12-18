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

agenthostname=`cat ~/agent_list | grep -i "^${agentname}=" | cut -d "=" -f 2`

# pull iso, assumption is that wget on internal network is fast

rm -rf iso_holder
mkdir iso_holder
cd iso_holder

if [[ $ceph_iso_file =~ "RHCEPH-*-x86_64-dvd.iso" ]]; then
    echo "**************$ceph_iso_file"
    wget -r -nd --no-parent -A "$ceph_iso_file" $ceph_iso_path &> /dev/null
    new_ceph_iso_file="$(ls)"
else
    wget $ceph_iso_path/$ceph_iso_file &> /dev/null
    new_ceph_iso_file=$ceph_iso_file
fi
if [ ! -f $new_ceph_iso_file ] ; then 
    echo "FAILED to fetch .iso file"
    exit 1
fi
ls

# clear out ceph-ansible staging area

ssh $agenthostname " 
	hostname
	cd ~/automated_ceph_test/staging_area
	mkdir -pv rhcs_latest rhcs_old || exit 1
	mv -v rhcs_latest/* rhcs_old/
	ls -l rhcs_old/ || echo ''
" || exit 1 

# copy iso to agent

echo "###################### $new_ceph_iso_file $agenthostname"
scp $new_ceph_iso_file $agenthostname:~/automated_ceph_test/staging_area/rhcs_latest || exit 1

# remove local dir

cd ../
rm -rf iso_holder

# version_adjust_repo allows user to specify a URL containing a repo
# that plugs gap between what new RHCS release requires 
# and what is available in centos

if [ -n "$version_adjust_repo" ] ; then
  version_adjust_dir=~/automated_ceph_test/version_adjust_repo
  version_adjust_name=`basename $version_adjust_repo`
  # FIXME: we could eliminate copy after first time, by using
  # correct wget parameters that only copy if file at source is more recent
  rm -rf $version_adjust_dir
  mkdir $version_adjust_dir
  pushd $version_adjust_dir || exit 1
  wget -q --no-parent --recursive --level=4 $version_adjust_repo/ || exit 1
  # wget inserts intermediate directories above target repo
  target_subdir=`find *redhat.com -name $version_adjust_name`
  mv -v $target_subdir .
  # since repo is assumed to be internal, it
  # always comes from redhat.com
  rm -rfv *.redhat.com
  ls -lR $version_adjust_name || exit 1
  popd

  # WISH THIS WORKED!
  # FIXME: only copy changes to remote agent
  #echo $USER $LOGNAME
  #(rsync -rac -vvv --del $version_adjust_dir/$version_adjust_name $agenthostname: && \
  #ssh $agenthostname 'ln -svf $version_adjust_name/version_adjust.repo /etc/yum.repos.d/') \
  #  || exit 1

  # either all these commands work or the job exits with failure status

  (ssh $agenthostname "rm -rf $version_adjust_name" && \
   scp -r $version_adjust_dir/$version_adjust_name $agenthostname: && \
   ssh $agenthostname "ln -svf \$HOME/$version_adjust_name/version_adjust.repo /etc/yum.repos.d/") \
     || exit 1
else
  ssh $agenthostname "rm -fv /etc/yum.repos.d/version_adjust.repo"
fi
ssh $agenthostname 'yum clean all'
