FROM mcr.microsoft.com/devcontainers/python:3.10

RUN mkdir -p /home/vscode/bin \
 && export FW_CLI_INSTALL_DIR=/home/vscode/bin \
 && curl https://storage.googleapis.com/flywheel-dist/fw-cli/stable/install.sh | bash \
 && chown -R vscode /home/vscode/bin
