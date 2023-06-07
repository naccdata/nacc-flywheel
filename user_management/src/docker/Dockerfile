FROM python:3.10

ENV BASE_DIR=/flywheel/v0
RUN mkdir -p ${BASE_DIR}/input

WORKDIR ${BASE_DIR}

COPY user_management/src/docker/manifest.json ${BASE_DIR}
COPY user_management.src.python/bin.pex /bin/run

ENTRYPOINT [ "/bin/run" ]