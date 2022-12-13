FROM mcr.microsoft.com/devcontainers/python:3.9

RUN mkdir -p /home/vscode/bin \
 && wget https://storage.googleapis.com/flywheel-dist/cli/16.7.5/fw-linux_amd64-16.7.5.zip -O /home/vscode/fw-linux_amd64-16.7.5.zip \
 && unzip -d /home/vscode /home/vscode/fw-linux_amd64-16.7.5.zip \
 && mv /home/vscode/linux_amd64/fw /home/vscode/bin \
 && rm /home/vscode/fw-linux_amd64-16.7.5.zip \
 && rmdir /home/vscode/linux_amd64
