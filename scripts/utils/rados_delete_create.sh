#!/bin/bash -x
objsz=$1
maxobjs=$2
maxtime=$3
delay_between_passes=$4

echo "object size $objsz, max objs $maxobjs, max secs $maxtime"
echo "delay between passes $delay_between_passes"

if [ -z "$4" ] ; then
  echo "usage: rados_delete_create.sh object-size max-objects max-seconds delay-between-passes"
  exit 1
fi

# find out who your monitor is

first_mon=`grep 'mon host' /etc/ceph/ceph.conf | tr ',' ' ' | awk '{print $4}'`
scp $first_mon:/etc/ceph/ceph.client.admin.keyring /etc/ceph/

# find out where osd.0 is, it must exist

first_osd=`ceph osd tree | awk '/host/{h=$4}/osd.0/{print h}'`
echo osd.0 at $first_osd
export osd0="ssh -o StrictHostKeyChecking=no $first_osd ceph daemon osd.0 "

function chkspace() {
	$osd0 perf dump | grep db_used | tr ':,' '  ' | awk '{ print $2}'
}

rm -f /tmp/rbench_*.log
for k in `seq 1 3` ; do 
  ceph osd pool rm ben ben --yes-i-really-really-mean-it
  ceph osd pool create ben 64 64
  ceph osd pool application enable ben radosbench
  sleep $delay_between_passes
  $osd0 flush_journal
  $osd0 compact
  ssh -o StrictHostKeyChecking=no li1017-241 systemctl restart ceph-osd@0
  sleep 5
  before_spc=`chkspace`
  if [ -z "$before_spc" ] ; then 
    echo 'no bluestore_db_used field, is this a Bluestore OSD?'
    exit 1 
  fi
  echo "space used before: $before_spc"
  rados bench -p ben --max-objects $2 -b $objsz -o $objsz $maxtime write --no-cleanup > /tmp/rbench_$k.log
  objct=`grep 'Total writes made:' /tmp/rbench_$k.log | awk '{ print $NF }'`
  echo "object count = $objct"
  $osd0 flush_journal
  $osd0 compact
  ceph df
  after_spc=`chkspace`
  echo "space used after: $after_spc"
  (( spc_per_obj = $after_spc - $before_spc ))
  echo "space consumed during pass: $spc_per_obj"
  (( spc_per_obj = $spc_per_obj / $objct ))
  echo "bytes per object used: $spc_per_obj"
done
  
