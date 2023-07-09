#!/bin/zsh

# set the source file and directory
SOURCE=$1
DIR=${2:-./images}

# set the output directory or use the default
OUT_DIR=${3:-./out}

# create the output directory if it does not exist
if [ ! -d $OUT_DIR ]; then
    mkdir $OUT_DIR
fi

# iterate over each file in the directory
for file in $DIR/*;
do
    # call the Python script with the source face and current file as input
    python3 faceswap.py $file $SOURCE $OUT_DIR/$(basename $file)
done