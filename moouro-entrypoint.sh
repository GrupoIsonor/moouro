#!/bin/sh
set -e

if command -v gosu >/dev/null 2>&1; then
    CMD_SU=gosu
else
    CMD_SU=su-exec
fi

# Init resticprofile (background)
if [ -f /etc/resticprofile/profiles.yaml ]; then
    (
        echo "[moouro] Init resticprofile..."
        $CMD_SU postgres resticprofile init --all || echo "[!][moouro] Error: resticprofile init has failed, ignoring..."
    ) &
fi

# Init pgbackrest (background)
if [ -f /etc/pgbackrest/pgbackrest.conf ]; then
    (
        until pg_isready -q -p 5432; do
            sleep 1
        done

        echo "[moouro] Postgres ready. Init pgBackRest..."
        # pg_isready can answer from the temporary initdb server, so retry until the real one is up
        for _ in $(seq 1 30); do
            $CMD_SU postgres pgbackrest --stanza=main stanza-create && exit 0
            sleep 2
        done
        echo "[!][moouro] Error: pgbackrest has failed, ignoring..."
    ) &
fi

echo "[moouro] Init PostgreSQL..."
if [ "${POSTGRES_BYPASS_ENTRYPOINT}" = "true" ]; then
    exec "$@"
else
    exec docker-entrypoint.sh "$@"
fi
