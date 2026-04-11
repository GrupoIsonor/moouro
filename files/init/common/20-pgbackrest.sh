#!/bin/sh
set -e

[ -f /etc/pgbackrest/pgbackrest.conf ] && pgbackrest --stanza=main stanza-create || true
