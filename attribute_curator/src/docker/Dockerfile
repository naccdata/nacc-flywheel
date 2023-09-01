FROM python:3.10

ENV BASE_DIR=/flywheel/v0
RUN mkdir -p ${BASE_DIR}/input

WORKDIR ${BASE_DIR}

COPY attribute_curator/src/docker/manifest.json ${BASE_DIR}
COPY attribute_curator.src.python.${APPNAME}/bin.pex /bin/run

ENTRYPOINT [ "/bin/run" ]