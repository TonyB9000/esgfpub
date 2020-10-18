#!/bin/bash

workpath=/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork

if [ $# -ne 1 ]; then
	echo "Usage:  multi_mapfile_publish.sh pub_path_listfile"
	exit 1
fi

pub_paths=$1

startTime=`date +%s`

ts=`date +%Y%m%d.%H%M%S`
rlog=$workpath/mfg_runlog-$ts

setcount=0;

for dataset in $pub_paths; do
        sleep 2
	ts=`date +%Y%m%d.%H%M%S`
	ds_tm1=`date +%s`
	echo "TS_$ts:STATUS: INPROCESS: dataset $dataset" >> $rlog 2>&1
	$workpath/make_mapfile_publish.sh $dataset >> $rlog 2>&1
        retcode=$?
	ds_tm2=`date +%s`
	ds_et=$(($ds_tm2 - $ds_tm1))

	ts=`date +%Y%m%d.%H%M%S`
	if [ $retcode -eq 0 ]; then
		echo "TS_$ts:STATUS: COMPLETED: dataset $dataset" >> $rlog 2>&1
	else
		echo "TS_$ts:STATUS: FAILURE:   dataset $dataset (exit code: $retcode)" >> $rlog 2>&1
	fi
	echo "TS_$ts:STATUS: dataset ET = $ds_et" >> $rlog 2>&1
	setcount=$(($setcount + 1))
done

finalTime=`date +%s`
et=$(($finalTime - $startTime))

echo " " >> $rlog 2>&1
echo "TS_$ts:STATUS: Processed $setcount datasets." >> $rlog 2>&1
echo "TS_$ts:STATUS: Elapsed Time: $et" >> $rlog 2>&1
