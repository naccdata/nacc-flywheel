file(name="manifest", source="manifest.json")

docker_image(
    name="pull-directory",
    source="Dockerfile",
    dependencies=[":manifest", "pull_directory/src/python/directory_app:bin"],
    image_tags=["0.0.6", "latest"])
