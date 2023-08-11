file(name="manifest", source="manifest.json")

docker_image(name="project-management",
             source="Dockerfile",
             dependencies=[":manifest", "project_management/src/python/project_app:bin"],
             image_tags=["0.0.1", "latest"])

experimental_run_shell_command(
    name="upload",
    command="fw-beta gear upload ./",
    description="run fw gear command for project_management",
    workdir="project_management/src/docker")

experimental_run_shell_command(
    name="validate",
    command="fw-beta gear --validate manifest.json",
    description="validate gear manifest for project_management",
    workdir="project_management/src/docker")

experimental_run_shell_command(
    name="local",
    command="fw-beta gear run",
    description="run project_management gear locally",
    workdir="project_management/src/docker")