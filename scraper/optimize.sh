#!/bin/bash

for file in $1/*.jpg
do
    echo $file
    mogrify $file -fuzz 25% -trim
done

