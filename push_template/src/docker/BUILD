file(name="manifest", source="manifest.json")

docker_image(name="push-template",
             source="Dockerfile",
             dependencies=[":manifest", "push_template/src/python:bin"],
             image_tags=["0.0.1", "latest"])

experimental_run_shell_command(
    name="gear",
    command="/home/vscode/bin/fw-beta gear",
    description="run fw gear command for push_template",
    workdir="push_template/src/docker")