file(name="manifest", source="manifest.json")

docker_image(name="csv-to-json-transformer",
             source="Dockerfile",
             dependencies=[
                 ":manifest",
                 "gear/csv_to_json_transformer/src/python/csv_app:bin"
             ],
             image_tags=["0.0.6", "latest"])
