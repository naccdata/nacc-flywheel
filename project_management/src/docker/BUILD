file(name="manifest", source="manifest.json")

docker_image(
    name="project_management",
    source="Dockerfile",
    dependencies=[":manifest", "project_management/src/python:bin"]
)
