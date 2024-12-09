FROM python:3.11

ENV BASE_DIR=/flywheel/v0
RUN mkdir -p ${BASE_DIR}/input

WORKDIR ${BASE_DIR}

COPY gear/redcap_import_error_checks/src/docker/manifest.json ${BASE_DIR}
COPY gear.redcap_import_error_checks.src.python.redcap_import_error_checks_app/bin.pex /bin/run

ENTRYPOINT [ "/bin/run" ]