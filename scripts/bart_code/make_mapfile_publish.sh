#!/bin/bash

# FORMAT
# esgmapfile make -i /path/to/ini/directory --max-processes <some_number_of_cores> --project <e3sm/cmip6> --outdir /output/location <path_to_data_directory>

dataset_fullpath=$1

ts=`date +%Y%m%d.%H%M%S`

echo "TS_$ts:INFO: make_mapfile: processing: $dataset_fullpath"
esgmapfile make --debug -i /p/user_pub/e3sm/staging/ini_std/ --max-processes 20 --project e3sm --outdir /p/user_pub/e3sm/staging/mapfiles/mapfiles_auto_publish $dataset_fullpath

exit $?


