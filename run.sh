#!/bin/bash
SOURCE=\$1
DIR=\$2

# iterate over each file in the directory
for file in $DIR/*;
do
    # call the Python script with the source face and current file as input
    python faceswap.py $SOURCE $file
    # copy the swapped image to a new file
    cp output.jpg "swapped_$file"
done