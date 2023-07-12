#!/usr/bin/env zsh

set -euo pipefail

# set the list of files
declare -A SOURCE_FILE_UUIDS
SOURCE_FILE_UUIDS=(
    "a1df40d4-c67e-11ea-902b-00505682fbe9"
    "95ddf580-edcd-11e6-adbc-00155d800308"
    "81271618-dc84-11e5-beed-00155d800305"
    "69ed6a14-674f-11e0-966e-00248ce13817"
    "4d5d355d-674e-11e0-966e-00248ce13817"
    "e1c4a7af-9e72-11ea-9028-00505682fbe9"
    "4d5d3557-674e-11e0-966e-00248ce13817"
    "fcb39cf8-6750-11e0-966e-00248ce13817"
    "14f82be5-239f-11e9-8a77-005056a0dbcd"
    "d7bd71e9-674f-11e0-966e-00248ce13817"
    "e1c4a7af-9e72-11ea-9028-00505682fbe9"
    "bf75aa41-6750-11e0-966e-00248ce13817"
    "1c8c84df-dd52-11ea-902b-00505682fbe9"
    "dba3420f-cdd8-11eb-904b-00505682fbe9"
    "d7bd71e4-674f-11e0-966e-00248ce13817"
    "de850f56-122c-11ed-9066-005056bb6e68"
    "95ddf580-edcd-11e6-adbc-00155d800308"
)
declare -r SOURCE_FILE_UUIDS

# set the input/output directory
IN_DIR="./images"
OUT_DIR="~/Public/s"

# remove empty files
find $IN_DIR -type f -empty -delete

function run {
    source ./venv/bin/activate

    # iterate over each file in list
    for source_file_uuid in $SOURCE_FILE_UUIDS; do 
        echo "\n\n****** Processing $source_file_uuid ***\n"

        local source_file=$IN_DIR/$source_file_uuid.jpg
        if [ ! -f $source_file ]; then
            echo "$source_file does not exist"
            continue
        fi

        # reset the output directory
        local output_dir=$OUT_DIR/$source_file_uuid
        rm -rf $output_dir
        if [ ! -d $output_dir ]; then
            mkdir -p $output_dir
        fi

        # call the Python script with the source face and current file as input
        python3 faceswap.py $source_file $IN_DIR $output_dir
    done
}

function view {
    images=()
    for source_file_uuid in $SOURCE_FILE_UUIDS; do
        images+=("$(find $OUT_DIR -iname "$source_file_uuid.jpg")")
    done

    feh -FZ $images
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
