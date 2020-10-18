#!/bin/bash

workpath=/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork

if [ $# -ne 1 ]; then
	echo "Usage:  multi_mapfile_Generate.sh map_status_control_file"
	exit 1
fi

pub_paths=$1
datasets=`grep -v DONE $map_status_file | grep -v HOLD`

startTime=`date +%s`

ts=`date +%Y%m%d.%H%M%S`
rlog=$workpath/mfg_runlog-$ts

setcount=0;

for dataset in $pub_paths; do
	ts=`date +%Y%m%d.%H%M%S`
	ds_tm1=`date +%s`
	echo "STATUS:$ts:INPROCESS: dataset $dataset" >> $rlog 2>&1
	$workpath/make_mapfile.sh $dataset >> $rlog 2>&1
        retcode=$?
	ds_tm2=`date +%s`
	ds_et=$(($ds_tm2 - $ds_tm1))

	ts=`date +%Y%m%d.%H%M%S`
	if [ $retcode -eq 0 ]; then
		echo "STATUS:$ts:COMPLETED: dataset $dataset" >> $rlog 2>&1
	else
		echo "STATUS:$ts:FAILURE:   dataset $dataset (exit code: $retcode)" >> $rlog 2>&1
	fi
	echo "STATUS: dataset ET = $ds_et" >> $rlog 2>&1
	setcount=$(($setcount + 1))
done

finalTime=`date +%s`
et=$(($finalTime - $startTime))

echo " " >> $rlog 2>&1
echo "Processed $setcount datasets." >> $rlog 2>&1
echo "Elapsed Time: $et" >> $rlog 2>&1
