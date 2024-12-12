file(name="manifest", source="manifest.json")

docker_image(
    name="form-csv-to-json-transformer",
    source="Dockerfile",
    dependencies=[
        ":manifest",
        "gear/form_csv_to_json_transformer/src/python/form_csv_app:bin"
    ],
    image_tags=["0.0.1", "latest"])
