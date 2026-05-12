#!/bin/sh
set -e

if [ "$POSTGRES_REPLICATION" = "true" ]; then
    if [ -n "$POSTGRES_MASTER_REPLICATOR_PASSWORD_FILE" ]; then
        PGPASSWORD=$(cat "$POSTGRES_MASTER_REPLICATOR_PASSWORD_FILE")
        export PGPASSWORD
    fi

    echo "Executing pg_basebackup..."
    if [ "$PG_MAJOR" = "9.6" ]; then
        pg_basebackup \
            -h "$POSTGRES_MASTER_HOST" \
            -p "${POSTGRES_MASTER_PORT:-5432}" \
            -U "${POSTGRES_MASTER_REPLICATOR_USER:-replicator}" \
            --no-password \
            -D "$PGDATA" \
            -Fp -Xs -R -v
    else
        pg_basebackup \
            -h "$POSTGRES_MASTER_HOST" \
            -p "${POSTGRES_MASTER_PORT:-5432}" \
            -U "${POSTGRES_MASTER_REPLICATOR_USER:-replicator}" \
            --no-password \
            -D "$PGDATA" \
            -Fp -Xs -R -v --wal-method=stream
    fi
    echo "pg_basebackup done"
fi
