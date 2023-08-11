file(name="manifest", source="manifest.json")

docker_image(name="push-template",
             source="Dockerfile",
             dependencies=[":manifest", "push_template/src/python/template_app:bin"],
             image_tags=["0.0.1", "latest"])

experimental_run_shell_command(
    name="validate",
    command="fw-beta gear --validate manifest.json",
    description="validate gear manifest for push_template",
    workdir="push_template/src/docker")

experimental_run_shell_command(
    name="local",
    command="fw-beta gear run",
    description="run push_template gear locally",
    workdir="push_template/src/docker")

experimental_run_shell_command(
    name="upload",
    command="fw-beta gear upload ./",
    description="run fw gear command for push_template",
    workdir="push_template/src/docker")