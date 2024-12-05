#!/usr/bin/env bash 

IMAGE=naccdata/center-management:1.0.2

# Command:
docker run --rm -v \
	/workspaces/flywheel-gear-extensions/gear/center_management/src/docker/input:/flywheel/v0/input \
	-v \
	/workspaces/flywheel-gear-extensions/gear/center_management/src/docker/config.json:/flywheel/v0/config.json \
	-v \
	/workspaces/flywheel-gear-extensions/gear/center_management/src/docker/manifest.json:/flywheel/v0/manifest.json \
	--entrypoint=/bin/sh -e FLYWHEEL='/flywheel/v0' $IMAGE -c \
	/bin/run \
