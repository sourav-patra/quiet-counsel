#!/bin/sh
# Install this repository's skills and agent roles. Every argument is passed to install.py;
# run it with --help for the options.
exec python3 "$(dirname "$0")/install.py" "$@"
