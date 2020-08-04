#!/bin/bash

Archive_Map=/p/user_pub/e3sm/archive/.cfg/Archive_Map
holodeck_stager="/p/user_pub/e3sm/bartoletti1/Pub_Work/1_Refactor/holodeck_stage_publication.sh"

pub_path_head="/p/user_pub/esgf/staging/prepub"

USAGE=$(cat <<-END
usage: (this_script) jobset_configfile file_of_Archive_Locator_selectedlines
   The jobset_config file must contain lines:
       dstype_static=<type>    (where <type> examples are "atm nat", "ocn nat", "lnd reg", etc)
       dstype_freq_list=<list> (where <list> examples are "mon", "day 6hr 6hr_snap", etc)
       resolution=<res>        (where res is one of 1deg_atm_60-30km_ocean or 0_25deg_atm_18-6km_ocean)
       pubvers=<ver>           (where ver is one of v1, v2, etc)
       overwriteFlag=<0|1>     (Boolean, allows adding files to a non-empty destination directory)
END
)

# echo "$USAGE"
# exit

rm -f nohup.out

echo " "
echo "# Publication Staging Controller #"
echo " "

if [ $# -eq 0 ]; then
	echo "$USAGE"
	exit
fi

if [ $1 == "help" ]; then
	echo "$USAGE"
	exit
fi

# obtain values for 
#   dstype_static	(e.g.  "atm nat", "ocn reg", etc)
#   dstype_freq_list	(e.g.  "mon", "mon day 6hr 3hr", "6hr_snap day_cosp", etc)
#   resolution          (e.g.  "1deg_atm_60-30km_ocean"   
#   pubversion
#   overwriteFlag=1

# job_spec
source $1

# file of Archive_Locator lines
AL_selected=$2

# NEW SYSTEM:  for each AL line, cycle over the dstype_freq_list to collect ALL relevant Archive_Map lines.
#  (some AM lines may appear repeatedly)
#  consuct a sort | uniq on the AM lines, and pass these individually to the holodeck stager.

startTime=`date +%s`
ts=`date +%Y%m%d.%H%M%S`
holodeck_log=/p/user_pub/e3sm/bartoletti1/Pub_Work/1_Refactor/Holodeck_Process_Log-$ts

rm -f /tmp/am_list

for AL_line in `cat $AL_selected`; do   # for a single Archive_Locator line

    # echo "DEBUG: Processing AL_line: $AL_line"

    # Campaign,Model,Experiment,Ensemble,Arch_Path
    AL_key=`echo $AL_line | cut -f1-4 -d,`

    for freq in $dstype_freq_list; do

        dstype="$dstype_static $freq"
        ds_key=`echo $dstype | tr ' ' _`
        AM_key="$AL_key,$ds_key,"
        # echo "Produced AM_key: $AM_key"
        grep $AM_key $Archive_Map >> /tmp/am_list
    done
done

IFS=$'\n'

Arch_Map_Selected=`sort /tmp/am_list | uniq`

# Here, we pass each Arch_Map_Selected line to the Holodeck Stager process.

datasets=0;

for AM_line in $Arch_Map_Selected; do   # for a single Archive_Map line

    # echo "DEBUG: Processing AM_line: $AM_line"

    # Campaign,Model,Experiment,Ensemble,DatasetSpec,Arch_Path,ExtractPattern

    ts=`date +%Y%m%d.%H%M%S`
    echo " " >> $holodeck_log 2>&1
    echo "$ts:Publication Staging Controller: Archive_Map_line = $AM_line" >> $holodeck_log 2>&1
    echo " " >> $holodeck_log 2>&1

    model=`echo $AM_line | cut -f2 -d,`
    exper=`echo $AM_line | cut -f3 -d,`
    ensem=`echo $AM_line | cut -f4 -d,`
    ds_spec=`echo $AM_line | cut -f5 -d,`
    arch_path=`echo $AM_line | cut -f6 -d,`
    x_pattern=`echo $AM_line | cut -f7 -d,`

    realmcode=`echo $ds_spec | cut -f1 -d_`
    grid=`echo $ds_spec | cut -f2 -d_`
    freq=`echo $ds_spec | cut -f3- -d_`

    if [ $realmcode == "atm" ]; then
        realm="atmos"
    elif [ $realmcode == "lnd" ]; then
        realm="land"
    elif [ $realmcode == "ocn" ]; then
        realm="ocean"
    elif [ $realmcode == "river" ]; then
        realm="river"
    elif [ $realmcode == "sea-ice" ]; then
        realm="sea-ice"
    else
        echo "ERROR: unrecognized realm code: $realmcode"
        exit 1
    fi

    pub_path="$pub_path_head/$model/$exper/$resolution/$realm/native/model-output/$freq/$ensem/$pubversion"       # not very flexible

    argslist=()
    argslist[0]=$arch_path
    argslist[1]=$x_pattern
    argslist[2]=$pub_path
    argslist[3]=$overwriteFlag

    ts=`date +%Y%m%d.%H%M%S`
    echo "$ts:Publication Staging Controller: Calling holodeck_stager with pub_path = $pub_path" >> $holodeck_log 2>&1
    $holodeck_stager "${argslist[@]}" >> $holodeck_log 2>&1

    ts=`date +%Y%m%d.%H%M%S`
    echo "$ts:Publication Staging Controller: Completion case spec: $AM_line" >> $holodeck_log 2>&1
    echo " " >> $holodeck_log 2>&1
    datasets=$(($datasets + 1))
done

finalTime=`date +%s`
et=$(($finalTime - $startTime))

echo "Elapsed time: $et seconds.  ($datasets datasets processed)" >> $holodeck_log


exit
	
