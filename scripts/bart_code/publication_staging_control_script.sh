#!/bin/bash


holodeck_stager="/p/user_pub/e3sm/bartoletti1/Pub_Work/1_Refactor/holodeck_stage_publication.sh"

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
#   pubvers=v1
#   overwriteFlag=1

source $1


# file of Archive_Locator lines
AL_selected=$2


startTime=`date +%s`
ts=`date +%Y%m%d.%H%M%S`
holodeck_log=/p/user_pub/e3sm/bartoletti1/Pub_Work/1_Refactor/Holodeck_Process_Log-$ts

# Here, we prepare to process one or more Archive_Locator lines, even when multiple lines may refer to 
# different parts of a single dataset

casecount=0;

for AL_line in `cat $AL_selected`; do   # for a single Archive_Locator line

	ts=`date +%Y%m%d.%H%M%S`
	echo " " >> $holodeck_log 2>&1
	echo "$ts:Publication Staging Controller: Archive_Locator_line = $AL_line" >> $holodeck_log 2>&1
	echo " "

	datasets=0;
	# For the current case (Experiment / Ensemble), we are prepared only to pull one or more
	# frequencies for a single realm (e.g.  cam.h1, h2, h3 ...)

	for freq in $dstype_freq_list; do
		argslist=()
		argslist[0]=$AL_line
		dstype="$dstype_static $freq"
		argslist[1]=$dstype
		argslist[2]=$resolution
		argslist[3]=$pubvers
		argslist[4]=$overwriteFlag
                # echo "argslist = ${argslist[@]}"

		ts=`date +%Y%m%d.%H%M%S`
		echo "$ts:Publication Staging Controller: Calling holodeck_stager with $AL_line \"$dstype\"" >> $holodeck_log 2>&1
		$holodeck_stager "${argslist[@]}" >> $holodeck_log 2>&1
		datasets=$(($datasets + 1))
	done
	ts=`date +%Y%m%d.%H%M%S`
	echo "$ts:Publication Staging Controller: Completion case spec: $AL_line ($datasets datasets)" >> $holodeck_log 2>&1
	echo " " >> $holodeck_log 2>&1
	casecount=$(($casecount + 1))
done

finalTime=`date +%s`
et=$(($finalTime - $startTime))

echo "Elapsed time: $et seconds.  ($casecount cases processed)" >> $holodeck_log


exit
	
