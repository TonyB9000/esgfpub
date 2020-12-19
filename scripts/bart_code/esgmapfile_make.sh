#!/bin/bash

# FORMAT
# esgmapfile_make.sh <dataset_fullpath>
# Note: output mapfile fullpath will be <dataset_fullpath>.mapfile

workpath=/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork
ini_path=/p/user_pub/e3sm/staging/ini_std/
out_path=/p/user_pub/e3sm/staging/mapfiles/mapfiles_output/

startTime=`date +%s`
ts=`date +%Y%m%d.%H%M%S`
rlog=$workpath/mfg_runlog-$ts

dataset_fullpath=$1

self_log=0

# Obtain the expected mapfile name, "<dsid>.map"
# must determine if "fullpath" begins with "/p/user_pub/e3sm" (warehouse) or "/p/user_pub/work" (publication)
# this is brittle - should be generalized
home=`echo $dataset_fullpath | cut -f4 -d/`
if [ $home == "e3sm" ]; then
    part=`echo $dataset_fullpath | cut -f7- -d/ | tr / .`
    dsid='E3SM.'${part}
elif [ $home == "work" ]; then
    dsid=`echo $dataset_fullpath | cut -f5- -d/ | tr / .`
else
    if [ $self_log -eq 1 ]; then
        echo "TS_$ts:ERROR:ESGMM: Unexpected dataset path: $dataset_fullpath" >> $rlog 2>&1
    else
        echo "TS_$ts:ERROR:ESGMM: Unexpected dataset path: $dataset_fullpath"
    fi
    exit 1
fi

mapfile_name=${dsid}.map
# echo $mapfile_name

ts=`date +%Y%m%d.%H%M%S`
if [ $self_log -eq 1 ]; then
    echo "TS_$ts:STATUS:ESGMM: make_mapfile: processing dataset $dataset_fullpath" >> $rlog 2>&1
else
    echo "TS_$ts:STATUS:ESGMM: make_mapfile: processing dataset $dataset_fullpath"
fi

ds_tm1=`date +%s`

#conda init bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pub
esgmapfile make --debug -i $ini_path --max-processes 60 --project e3sm --outdir $out_path $dataset_fullpath
retcode=$?
conda deactivate

mv $out_path/$mapfile_name $dataset_fullpath/.mapfile

ds_tm2=`date +%s`
ds_et=$(($ds_tm2 - $ds_tm1))

ts=`date +%Y%m%d.%H%M%S`
if [ $retcode -eq 0 ]; then
    if [ $self_log -eq 1 ]; then
        echo "TS_$ts:STATUS:ESGMM: COMPLETED: dataset $dataset_fullpath" >> $rlog 2>&1
    else
        echo "TS_$ts:STATUS:ESGMM: COMPLETED: dataset $dataset_fullpath"
    fi
else
    if [ $self_log -eq 1 ]; then
        echo "TS_$ts:STATUS:ESGMM: FAILURE:   dataset $dataset_fullpath (exit code: $retcode)" >> $rlog 2>&1
    else
        echo "TS_$ts:STATUS:ESGMM: FAILURE:   dataset $dataset_fullpath (exit code: $retcode)"
    fi
fi

if [ $self_log -eq 1 ]; then
    echo "TS_$ts:STATUS:ESGMM: dataset ET = $ds_et" >> $rlog 2>&1
else
    echo "TS_$ts:STATUS:ESGMM: dataset ET = $ds_et"
fi


exit $retcode


