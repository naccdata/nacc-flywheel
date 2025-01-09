file(name="manifest", source="manifest.json")

docker_image(name="prescreening",
             source="Dockerfile",
             dependencies=[
                 ":manifest",
                 "gear/prescreening/src/python/prescreening_app:bin"
             ],
             image_tags=["0.0.3", "latest"])
