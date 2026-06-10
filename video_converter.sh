#!/bin/bash

for file in *.mp4; do
    filename="${file%.mp4}"

    output="${filename}.3gp"

    echo "converting $file to $output..."

    ffmpeg -i "$file" -vf scale=240:320 -c:v mpeg4 -b:v 600k -c:a aac -b:a 128k -ar 44100 -ac 1 "$output"

    echo "Done convertiing $file"
done

echo "All convertions completed."