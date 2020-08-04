#!/bin/bash

# Obtain values for
#   resolution		(e.g. 1deg_atm_60-30km_ocean, 0_25deg_atm_18-6km_ocean, etc)
#   pubversion		(e.g. v1, v2, etc)
#   overwriteFlag	(Boolean)

Datatype_Patterns=/p/user_pub/e3sm/archive/.cfg/Standard_Datatype_Extraction_Patterns
The_Holodeck=/p/user_pub/e3sm/bartoletti1/Pub_Work/1_Refactor/Holodeck

Archive_Map=/p/user_pub/e3sm/archive/.cfg/Archive_Map
prepubroot=/p/user_pub/e3sm/staging/prepub
pubroot=/p/user_pub/work/E3SM

# echo "DEBUG:  argcount = $#"

if [ $# -ne 5 ]; then
	echo " "
	echo "    Usage:  holodeck_stage_publication.sh jobset_config AL_selection_line datasetspec resolution pubversion overwriteflag"
	echo " "
	echo "            AL_selection_line is a line selected from archive/.cfg/Archive_Locator."
	echo "            Give datasetspec as \"realm grid freq\", as in \"atm nat mon\", in quotations."
	echo "            (See the file /p/user_pub/e3sm/archive/.cfg/Standard_Datatype_Extraction_Patterns)"
	echo "            resolution=<res>        (where res is one of 1deg_atm_60-30km_ocean or 0_25deg_atm_18-6km_ocean)"
	echo "            pubversion=<ver>           (where ver is one of v1, v2, etc)"
	echo "            overwriteFlag=<0|1>     (Boolean, allows adding files to a non-empty destination directory)"
	echo " "
	exit 0
fi

# echo "DEBUG: DOLLAR_1 = $1"
# echo "DEBUG: DOLLAR_2 = $2"


zstash_version=`zstash version`
if [ $zstash_version != "v0.4.1" ]; then
	echo "ABORTING:  zstash version is not 0.4.1 or is unavailable"
	exit 1
fi

IFS=$'\n'


AL_selection_line=$1
ds_spec=$2	# realm-code nat freq_code, e.g. "atm nat mon", from Standard_Datatype_Extraction_Patterns
resolution=$3
pubversion=$4
overwrite=$5

AL_path=`echo $AL_selection_line | cut -f5 -d,`
AL_key=`echo $AL_selection_line | cut -f1-4 -d,`

ds_key=`echo $ds_spec | tr ' ' _`

AM_key="$AL_key,$ds_key,"
# echo "Produced AM_key: $AM_key"

# Determine realm for  midpath
realm_code=`echo $ds_spec | cut -f1 -d' '`

if [ $realm_code == "atm" ]; then
	realm="atmos"
elif [ $realm_code == "lnd" ]; then
	realm="land"
elif [ $realm_code == "ocn" ]; then
	realm="ocean"
elif [ $realm_code == "river" ]; then
	realm="river"
elif [ $realm_code == "sea-ice" ]; then
	realm="sea-ice"
else
	echo "ERROR: unrecognized realm code: $realm_code"
	exit 1
fi


midpath=$resolution/$realm/native/model-output

AM_list=`grep $AM_key $Archive_Map | sort`

# listcount=`echo $AM_list | wc -l`
# echo "Matched $listcount AM lines"

#exit 0

# may activate multiple Archive_Map lines, must loop.

cd $The_Holodeck

for am_line in $AM_list; do

	# echo "DEBUG: am_line = $am_line"

	campaign=`echo $am_line | cut -f1 -d,`
	modelver=`echo $am_line | cut -f2 -d,`
	exp_name=`echo $am_line | cut -f3 -d,`
	ensemble=`echo $am_line | cut -f4 -d,`
	arch_dir=`echo $am_line | cut -f6 -d,`
	tar_patt=`echo $am_line | cut -f7 -d,`

	# PLAN Step 1: test and exit if publication directory already exists.

	freq=`echo $ds_spec | cut -f3 -d' '`
	targ_pub_dir="$prepubroot/$modelver/$exp_name/$midpath/$freq/$ensemble/$pubversion"

	# echo "DEBUG: freqword = $freq"

	if [ $overwrite -eq 0 ]; then
		if [ -d $targ_pub_dir ]; then
			fc=`ls $targ_pub_dir | wc -l`
			if [ $fc -gt 0 ]; then
				echo "ABORT: PUB DIR EXISTS ($fc files) $targ_pub_dir"
				echo " "
				continue
			fi
		fi
	fi

	# PLAN Step 2: Use the supplied Archive_Locator line to obtain the information regarding the archive source data

	echo "Conducting zstash extract for directory $arch_dir with dataset extraction pattern $tar_patt"
	echo "Target Publication Dir:  $targ_pub_dir"
        echo " "

	# continue



	# Real Stuff Below

	# PLAN Step 3:  populate the subordinate "zstash" subdirectory with simlinks to the appropriate tarfiles and index.db file.
	#    - Ensure holodeck contains only empty zstash subdirectory

	echo "Cleaning the Holodeck"
	echo " "
	rm -rf $The_Holodeck/*

	zstash_dir=$The_Holodeck/zstash
	mkdir $zstash_dir

	for targ in `ls $arch_dir`; do
		# touch nothing
		# echo "ln -s $arch_dir/$targ zstash/$targ"
		ln -s $arch_dir/$targ $zstash_dir/$targ
	done

	# Conduct extraction via the Holodeck

	echo "zstash extract --hpss=none $tar_patt"
	zstash extract --hpss=none $tar_patt
	exitcode=$?

	if [ $exitcode -ne 0 ]; then
		echo "ERROR:  zstash returned exitcode $exitcode"
		exit $exitcode
	fi


	echo "MKDIR: mkdir -p $targ_pub_dir"
	mkdir -p $targ_pub_dir
	chmod 755 $targ_pub_dir

	echo "mv $The_Holodeck/$file_extract_pattern $targ_pub_dir"
	mv $The_Holodeck/$tar_patt $targ_pub_dir
	chmod 644 $targ_pub_dir/*
	echo " "

	echo "Cleaning the Holodeck"
	echo " "
	rm -rf $The_Holodeck/*
done

exit 0
