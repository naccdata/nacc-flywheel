#!/bin/bash
if [ ! -d "src/docker" ]; then
    echo "Error: Directory 'src/docker' not found. Must be run within gear/project directory."
    exit 1
fi

build_tag=`pants peek src/docker:: | jq '.[] | select(.image_tags) | .image_tags[]' | grep -v "latest" | sort | uniq`
echo "Build tag: $build_tag"
version_tag=`cat src/docker/manifest.json | jq '.version'`
echo "Version tag: $version_tag"
image_tag=`cat src/docker/manifest.json | jq '.custom | ."gear-builder" | .image'`
echo "Image tag: $image_tag"