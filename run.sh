#!/usr/bin/env zsh

set -euo pipefail

# set the list of files
declare -a SOURCE_FILES
SOURCE_FILES=(
    "input/a1df40d4-c67e-11ea-902b-00505682fbe9.jpg"
    "input/95ddf580-edcd-11e6-adbc-00155d800308.jpg"
    "input/81271618-dc84-11e5-beed-00155d800305.jpg"
    "input/69ed6a14-674f-11e0-966e-00248ce13817.jpg"
    "input/4d5d355d-674e-11e0-966e-00248ce13817.jpg"
    "input/e1c4a7af-9e72-11ea-9028-00505682fbe9.jpg"
    "input/4d5d3557-674e-11e0-966e-00248ce13817.jpg"
    "input/fcb39cf8-6750-11e0-966e-00248ce13817.jpg"
    "input/14f82be5-239f-11e9-8a77-005056a0dbcd.jpg"
    "input/d7bd71e9-674f-11e0-966e-00248ce13817.jpg"
    "input/e1c4a7af-9e72-11ea-9028-00505682fbe9.jpg"
    "input/bf75aa41-6750-11e0-966e-00248ce13817.jpg"
    "input/1c8c84df-dd52-11ea-902b-00505682fbe9.jpg"
    "input/dba3420f-cdd8-11eb-904b-00505682fbe9.jpg"
    "input/d7bd71e4-674f-11e0-966e-00248ce13817.jpg"
    "input/de850f56-122c-11ed-9066-005056bb6e68.jpg"
    "input/95ddf580-edcd-11e6-adbc-00155d800308.jpg"
)
declare -r SOURCE_FILES

# set the input/output directory
IN_DIR="input"
OUT_DIR="output"

# remove empty files except .gitkeep
find $IN_DIR -type f -not -name .gitkeep -empty -delete

function run {
    # iterate over each file in list
    for source_file in $SOURCE_FILES; do 
        # check if file exists
        if [ ! -f $source_file ]; then
            echo "$source_file does not exist"
            continue
        fi

        # reset the output directory
        local output_dir=$OUT_DIR/$(basename ${source_file%.*})
        rm -rf $output_dir
        if [ ! -d $output_dir ]; then
            mkdir -p $output_dir
        fi

        # call the Python script with the source face and current file as input
        echo "\n*** Processing\n$source_file\n"
        python3 faceswap "$source_file" "$IN_DIR" "$output_dir"
        echo "*** Done\n"
    done
}

function view {
    declare -a images
    images=()
    for source_file in $SOURCE_FILES; do
        images+=$(find $OUT_DIR -iname "$(basename "$source_file")")
    done

    declare -r SOURCE_FILES
    echo "\n\n*** View images\n$images\n"
    echo "$images"
    feh -FZ "$images"
}

echo "1. Run"
echo "2. View"
read "option?Select an option: " 

case $option in
  1)
    run
    ;;
  2)
    view
    ;;
  *)
    echo "Invalid option $option"
    ;;
esac
