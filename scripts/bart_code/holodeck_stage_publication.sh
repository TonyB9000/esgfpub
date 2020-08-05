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

    argslist[0]=$arch_path
    argslist[1]=$x_pattern
    argslist[2]=$pub_path
    argslist[3]=$overwriteFlag

if [ $# -ne 4 ]; then
	echo " "
	echo "    Usage:  holodeck_stage_publication.sh archivePath extractionPattern (tail)publicationPath overwriteFlag[0|1]"
	echo " "
	echo "            archivePath:        Full path to an archive directory (from Archive_Map)"
	echo "            extractionPattern:  Dataset file-matching pattern (from Archive_Map))"
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


arch_path=$1
x_pattern=$2
pub_path=$3
overwrite=$4


cd $The_Holodeck

if [ $overwrite -eq 0 ]; then
    if [ -d $pub_path ]; then
        fc=`ls $pub_path | wc -l`
        if [ $fc -gt 0 ]; then
            echo "ABORT: PUB DIR EXISTS ($fc files) $pub_path"
            echo " "
            exit 0
        fi
    fi
fi


echo "Conducting zstash extract for directory $arch_path with dataset extraction pattern $x_pattern"
echo "Target Publication Dir:  $pub_path"
echo " "

# exit 0


# Real Stuff Below

# PLAN Step 3:  populate the subordinate "zstash" subdirectory with simlinks to the appropriate tarfiles and index.db file.
#    - Ensure holodeck contains only empty zstash subdirectory

echo "Cleaning the Holodeck"
echo " "
rm -rf $The_Holodeck/*

zstash_dir=$The_Holodeck/zstash
mkdir $zstash_dir

for targ in `ls $arch_path`; do
        # echo "ln -s $arch_path/$targ zstash/$targ"
        ln -s $arch_path/$targ $zstash_dir/$targ
done

# Conduct extraction via the Holodeck

echo "zstash extract --hpss=none $x_pattern"
zstash extract --hpss=none $x_pattern
exitcode=$?

if [ $exitcode -ne 0 ]; then
        echo "ERROR:  zstash returned exitcode $exitcode"
        exit $exitcode
fi


echo "MKDIR: mkdir -p $pub_path"
mkdir -p $pub_path
chmod 755 $pub_path

echo "mv $The_Holodeck/$x_pattern $pub_path"
mv $The_Holodeck/$x_pattern $pub_path
chmod 644 $pub_path/*
echo " "

echo "Cleaning the Holodeck"
echo " "
rm -rf $The_Holodeck/*

exit 0
