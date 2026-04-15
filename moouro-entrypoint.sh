#!/bin/sh
set -e

if [ -f /etc/resticprofile/profiles.yaml ]; then
    # Sub-shell
    (
        echo "[moouro] Init resticprofile..."
        resticprofile init --all || echo "[!][moouro] Error: resticprofile init has failed, ignoring..."
        resticprofile check
    ) &
fi

if [ -f /etc/pgbackrest/pgbackrest.conf ]; then
    # Sub-shell
    (
        # Wait psql
        until pg_isready -p 5432 -U ${POSTGRES_USER:-postgres}; do
        sleep 1
        done

        echo "[moouro] Postgres ready. Init pgBackRest..."
        # Creamos la stanza solo si no existe
        pgbackrest --stanza=main stanza-create || echo "[!][moouro] Error: pgbackrest has failed, ignoring..."
        pgbackrest --stanza=main check
    ) &
fi

echo "[moouro] Init PostgreSQL..."
exec docker-entrypoint.sh "$@"
