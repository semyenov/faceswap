#!/usr/bin/env zsh

# set the zsh options
set -euo pipefail

# set the input/output directory
IN_DIR="input"
OUT_DIR="output"

# set the list of files
declare -a SOURCE_FILES
IFS=$'\n' read -A SOURCE_FILES <<< "$(FZF_DEFAULT_COMMAND="find $IN_DIR -type f -not -name .gitkeep" fzf -m --preview "cat {}" --prompt="Select source files > " --preview-window=right:50%:wrap)"
declare -r SOURCE_FILES

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
        echo "***\nProcessing $source_file"
        python3 faceswap "./$source_file" "./$IN_DIR" "./$output_dir"
        echo ""
    done
}

function view {
    declare -a images
    local images=()
    for source_file in $SOURCE_FILES; do
        images+=($(find $OUT_DIR -iname "$(basename "$source_file")"))
    done
    declare -r images

    echo "***\nViewing $images\n"
    feh -FZ "$images"
}

echo -n "***\nSelect source files > "
for source_file in $SOURCE_FILES; do
    echo -n "$source_file "
done

echo "\n\n***\n1. Run"
echo "2. View"
read "option?Select an option > " 
echo ""

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
