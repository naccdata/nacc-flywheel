file(name="manifest", source="manifest.json")

docker_image(name="redcap-refresh-dl-urls",
             source="Dockerfile",
             dependencies=[":manifest", "gear/redcap_refresh_dl_urls/src/python/redcap_refresh_dl_urls_app:bin"],
             image_tags=["0.0.5", "latest"],
             build_platform=["linux/amd64"]
             )
