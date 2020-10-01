#!/bin/bash

infile=$1

for aline in `cat $infile`; do
    outline=`echo $aline | cut -f2- -d: | tr : ,`
    echo $outline
done
