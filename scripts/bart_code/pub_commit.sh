#!/bin/bash

# FORMAT
# given a full publication path, produce mapfile_ name <dsid>.map
# move publication path/.mapfile to auto_pub/mapfile_name

workpath=/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork
ini_path=/p/user_pub/e3sm/staging/ini_std/
out_path=/p/user_pub/e3sm/staging/mapfiles/mapfiles_output/
auto_pub=/p/user_pub/e3sm/staging/mapfiles/mapfiles_auto_publish/

startTime=`date +%s`
ts=`date +%Y%m%d.%H%M%S`
rlog=$workpath/runlog_pub_commit-$ts

dataset_fullpath=$1
map_path=${dataset_fullpath}/.mapfile

ts=`date +%Y%m%d.%H%M%S`
echo "TS_$ts:STATUS: pub_commit: processing dataset $dataset_fullpath" >> $rlog 2>&1
ds_tm1=`date +%s`

if [ ! -f $map_path ]; then
    echo "TS_$ts:STATUS: FAILURE: mapfile not found: $map_path" >> $rlog 2>&1
    exit 1
fi


# Obtain the expected mapfile name, "<dsid>.map"
dsid=`echo $dataset_fullpath | cut -f5- -d/ | tr / .`
mapfile_name=${dsid}.map
echo $mapfile_name

mv $map_path $auto_pub/$mapfile_name
retcode=$?

ds_tm2=`date +%s`
ds_et=$(($ds_tm2 - $ds_tm1))

ts=`date +%Y%m%d.%H%M%S`
if [ $retcode -eq 0 ]; then
        echo "TS_$ts:STATUS: COMPLETED: moved to auto_publish: $mapfile_name" >> $rlog 2>&1
else
        echo "TS_$ts:STATUS: FAILURE:   could not move to auto_publish: $mapfile_name (exit code: $retcode)" >> $rlog 2>&1
fi
echo "TS_$ts:STATUS: dataset ET = $ds_et" >> $rlog 2>&1

exit $retcode


