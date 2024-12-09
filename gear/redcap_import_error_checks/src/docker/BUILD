file(name="manifest", source="manifest.json")

docker_image(name="redcap-import-error-checks",
             source="Dockerfile",
             dependencies=[":manifest", "gear/redcap_import_error_checks/src/python/redcap_import_error_checks_app:bin"],
             image_tags=["0.1.0", "latest"])
