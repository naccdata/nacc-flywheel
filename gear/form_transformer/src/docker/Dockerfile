FROM python:3.11

ENV BASE_DIR=/flywheel/v0
RUN mkdir -p ${BASE_DIR}/input

WORKDIR ${BASE_DIR}

COPY gear/form_csv_to_json_transformer/src/docker/manifest.json ${BASE_DIR}
COPY gear.form_csv_to_json_transformer.src.python.form_csv_app/bin.pex /bin/run

ENTRYPOINT [ "/bin/run" ]