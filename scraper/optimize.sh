#!/bin/bash

in_dir=$1
out_dir=$2
mkdir -p $out_dir

for file in $in_dir/*.jpg
do
    in_file=$file
    out_file=$(sed -e "s#^$in_dir#$out_dir#" <<< $in_file)
    echo $in_file "->" $out_file
    convert $in_file -fuzz 25% -trim $out_file
done
