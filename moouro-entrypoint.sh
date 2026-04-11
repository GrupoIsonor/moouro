#!/bin/sh
set -e

[ -f /etc/resticprofile/profiles.yaml ] && resticprofile init --all || true

exec docker-entrypoint.sh "$@"
