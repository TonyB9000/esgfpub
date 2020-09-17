#!/bin/bash

sprok=/p/user_pub/e3sm/bartoletti1/abin/sproket-linux-0.2.13
config=/p/user_pub/e3sm/bartoletti1/abin/.sproket_config.json

# PYTHON: datetime.now().strftime('%Y%m%d_%H%M%S')

ts=`date +%Y%m%d.%H%M%S`

# to obtain ALL file names
$sprok -config $config -urls.only -no.download -no.verify -p 12 -y > E3SM_datafile_urls-$ts

exit 0







# to obtain the datasetIDs
# $sprok -config $config -values.for dataset_id_template_ -no.download -no.verify -y > E3SM_datasets


$sprok -config $config -field.keys > E3SM_fields

IFS=$'\n'

rm -f E3SM_field_values

for afield in `cat E3SM_Fields_useful`; do
	echo " " >> E3SM_field_values
	echo "FIELD_$afield" >> E3SM_field_values
	echo " " >> E3SM_field_values
	$sprok -config $config -values.for $afield >> E3SM_field_values
done


