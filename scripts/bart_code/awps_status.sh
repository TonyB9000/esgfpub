#!/bin/bash

work_dir=/p/user_pub/e3sm/bartoletti1/Pub_Status/

awps_gen=$work_dir/awps_dataset_status.py

sprokdir=$work_dir/sproket

esgf_rep=`ls $sprokdir | grep ESGF_publication_report- | tail -1`

ts=`date +%Y%m%d.%H%M%S`

out_temp="tempfile-$ts"

python $awps_gen -s $sprokdir/$esgf_rep > $out_temp

sort $out_temp | uniq | grep -v ____ > AWPS_Status-$ts

rm $out_temp

stattypes=`cat AWPS_Status-$ts | cut -f1 -d: | sort | uniq`

for atype in $stattypes; do
    tcount=`cat AWPS_Status-$ts | grep $atype | wc -l`
    stype=`echo $atype | cut -f2 -d=`
    echo "$stype: $tcount datasets" >> AWPS_Status_Summary-$ts
done

echo "AWPS report completed: AWPS_Status-$ts"

exit 0
