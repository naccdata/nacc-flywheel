file(name="manifest", source="manifest.json")

docker_image(name="user-management",
             source="Dockerfile",
             dependencies=[":manifest", "user_management/src/python:bin"],
             image_tags=["0.0.1", "latest"])

experimental_run_shell_command(
    name="gear",
    command="fw-beta gear",
    description="run fw gear command for user_management",
    workdir="user_management/src/docker")
