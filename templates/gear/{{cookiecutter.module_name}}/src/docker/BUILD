file(name="manifest", source="manifest.json")

docker_image(name="{{cookiecutter.package_name}}",
             source="Dockerfile",
             dependencies=[":manifest", "gear/{{cookiecutter.module_name}}/src/python/{{cookiecutter.module_name}}:bin"],
             image_tags=["{{cookiecutter.image_tag}}", "latest"])
