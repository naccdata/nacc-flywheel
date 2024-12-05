#!/usr/bin/env bash 

IMAGE=naccdata/apoe-transformer:0.1.0

# Command:
docker run --rm -v \
	/workspaces/flywheel-gear-extensions/gear/apoe_transformer/src/docker/input:/flywheel/v0/input \
	-v \
	/workspaces/flywheel-gear-extensions/gear/apoe_transformer/src/docker/config.json:/flywheel/v0/config.json \
	-v \
	/workspaces/flywheel-gear-extensions/gear/apoe_transformer/src/docker/manifest.json:/flywheel/v0/manifest.json \
	--entrypoint=/bin/sh -e FLYWHEEL='/flywheel/v0' $IMAGE -c \
	/bin/run \
