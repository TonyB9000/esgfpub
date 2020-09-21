#!/bin/bash

cfg_head="cfg_head"
cfg_tail="cfg_tail"
scr_head="scr_head"
scr_tail="scr_tail"
experiments=`cat experiments`

rm -f config*
rm -f script*
rm -f output*
rm -f flagon*

rm -f list_scripts

IFS=$'\n'

for exper in $experiments; do
    # Create custom config
    cfg_name="config-$exper"
    cat $cfg_head > $cfg_name
    echo "        \"experiment\": \"$exper\"," >> $cfg_name
    cat $cfg_tail >> $cfg_name
    chmod 640 $cfg_name

    scr_name="script-${exper}.sh"
    cat $scr_head > $scr_name
    echo "config=\"$cfg_name\"" >> $scr_name
    echo "output=\"output-$exper\"" >> $scr_name
    echo "flagon=\"flagon-$exper\"" >> $scr_name
    cat $scr_tail >> $scr_name
    chmod 750 $scr_name

    echo $scr_name >> list_scripts
done

start_tm=`date +%s`

for ascript in `cat list_scripts`; do
    ./$ascript &
    sleep 1
done

while [ 1 ]; do
    flagcount=`ls flagon* 2>/dev/null | wc -l`
    if [ $flagcount -eq 0 ]; then
        break
    fi
    echo "running = $flagcount"
    sleep 60
done

# should now have pile of output-whatever

ts=`date +%Y%m%d.%H%M%S`

cat output* | sort > ../E3SM_datafile_urls-$ts

final_tm=`date +%s`

et=$((final_tm - start_tm))

echo "PARA COMPLETED: ET = $et seconds"

exit 0

