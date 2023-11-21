file(name="manifest", source="manifest.json")

docker_image(name="identifer-lookup",
             source="Dockerfile",
             dependencies=[":manifest", "identifer_lookup/src/python/identifer_app:bin"],
             image_tags=["0.0.1", "latest"])
