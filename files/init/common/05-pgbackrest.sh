#!/bin/sh
set -e

# This is necessary to ensure that pgbackrest initializes correctly.
# This should be run first, since database operations will modify the WAL,
# and the configuration already includes the `archive_command`.
[ -f /etc/pgbackrest/pgbackrest.conf ] && pgbackrest --stanza=main stanza-create || true
