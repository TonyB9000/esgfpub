#!/bin/bash

# Usage:  process_sproket_output.sh  E3SM_datafile_urls-<timestamp>o

datafile_urls=$1

ts=`date +%Y%m%d.%H%M%S`
dataset_paths_full="E3SM_dataset_paths_full-$ts"
dataset_paths_leaf="E3SM_dataset_paths_leaf-$ts"
publication_dsids="E3SM_dataset_ids-$ts"
publication_report="ESGF_publication_report-$ts"

cat $datafile_urls | cut -f7- -d/ | sort | uniq > $dataset_paths_full
cat $dataset_paths_full | rev | cut -f2- -d/ | rev | sort | uniq > $dataset_paths_leaf


for aline in `cat $dataset_paths_leaf`; do
	filecount=`grep $aline $dataset_paths_full | wc -l`
	firstfile=`grep $aline $dataset_paths_full | rev | cut -f1 -d/ | rev | sort | uniq | head -1`
	finalfile=`grep $aline $dataset_paths_full | rev | cut -f1 -d/ | rev | sort | uniq | tail -1`
	datasetID=`echo $aline | tr / .`

	# handle variable sim-date year counts

	if [[ $firstfile =~ -*([0-9]{4}-[0-9]{2}) ]]; then

		# process YYYY-MM
		yearmo1=`echo ${BASH_REMATCH[1]}`
		if [[ $finalfile =~ -*([0-9]{4}-[0-9]{2}) ]]; then
			yearmo2=`echo ${BASH_REMATCH[1]}`
		else
			echo "NOMATCH,$filecount,$datasetID,$firstfile" >> $publication_report
			continue
		fi

		y1=`echo $yearmo1 | cut -c1-4`
		y2=`echo $yearmo2 | cut -c1-4`
		m2=`echo $yearmo2 | cut -c6-7`

		if [ $m2 == "01" ]; then
			yspan=$((y2 - y1))
		else
			yspan=$((y2 - y1 + 1))
		fi

		echo "$yspan,$filecount,$datasetID,$firstfile" >> $publication_report
		

	elif [[ $firstfile =~ -*([0-9]{6}_[0-9]{6}) ]]; then

		# process YYYYMM-YYYYMM first file only
		ym_ym=`echo ${BASH_REMATCH[1]}`

		y1=`echo $ym_ym | cut -c1-4`
		y2=`echo $ym_ym | cut -c8-11`
		m2=`echo $ym_ym | cut -c12-13`

		if [ $m2 == "01" ]; then
			yspan=$((y2 - y1))
		else
			yspan=$((y2 - y1 + 1))
		fi

		echo "$yspan,$filecount,$datasetID,$firstfile" >> $publication_report
	else
		echo "NOMATCH,$filecount,$datasetID,$firstfile" >> $publication_report
		continue
	fi

done


