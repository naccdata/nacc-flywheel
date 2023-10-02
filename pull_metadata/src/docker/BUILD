file(name="manifest", source="manifest.json")

docker_image(name="pull-metadata",
             source="Dockerfile",
             dependencies=[
                 ":manifest", "pull_metadata/src/python/project_app:bin"
             ],
             image_tags=["0.0.1", "latest"])
