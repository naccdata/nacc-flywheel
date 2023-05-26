file(name="manifest", source="manifest.json")

docker_image(name="project-management",
             source="Dockerfile",
             dependencies=[":manifest", "project_management/src/python:bin"],
             image_tags=["0.0.1", "latest"])

experimental_run_shell_command(
    name="gear",
    command="/home/vscode/bin/fw-beta gear",
    description="run fw gear command for project_management",
    workdir="project_management/src/docker")
