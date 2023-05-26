#!/bin/bash

echo "making new gear directories named '$1'"

DIRNAME=$1
IMAGENAME=`echo $1 | tr '_' '-'`

mkdir -p $1/src/python
touch $1/src/python/main.py
touch $1/src/python/run.py

mkdir -p $1/test/python
touch $1/test/python/.gitkeep

mkdir -p $1/src/docker
cat templates/docker/build-template.txt | envsubst > $1/src/docker/BUILD
cat templates/docker/dockerfile-template.txt | envsubst '${DIRNAME}' > $1/src/docker/Dockerfile
cat templates/docker/manifest-template.txt | envsubst > $1/src/docker/manifest.json

mkdir -p docs/$1
touch docs/$1/index.md
echo "# $1" > docs/$1/index.md
