#!/bin/sh
ROOTS=$(pants roots --roots-sep=' ')
python3 -c "print('PYTHONPATH=\"./' + ':./'.join(\"${ROOTS}\".split()) + ':\$PYTHONPATH\"')" > .env

pants generate-lockfiles
pants export --symlink-python-virtualenv --resolve=python-default

ln -snf dist/export/python/virtualenvs/python-default /workspaces/flywheel-gear-extensions/venv
