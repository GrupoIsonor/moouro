#!/bin/sh
set -e

if [ -n "$POSTGRES_ODOO_PASSWORD_FILE" ]; then
    POSTGRES_ODOO_PASSWORD=$(cat "$POSTGRES_ODOO_PASSWORD_FILE")
fi

if [ -n "${POSTGRES_ODOO_USER:-}" ] && [ -n "${POSTGRES_ODOO_PASSWORD:-}" ]; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE USER ${POSTGRES_ODOO_USER} WITH PASSWORD '${POSTGRES_ODOO_PASSWORD}';
        ALTER USER ${POSTGRES_ODOO_USER} CREATEDB;
EOSQL

    if [ -n "${POSTGRES_ODOO_DB:-}" ]; then
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
            CREATE DATABASE ${POSTGRES_ODOO_DB}
                WITH OWNER = ${POSTGRES_ODOO_USER}
                    ENCODING = 'UTF8'
                    LC_COLLATE = 'C'
                    LC_CTYPE = 'C'
                    TEMPLATE = template0;
EOSQL

        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_ODOO_DB" <<-EOSQL
            CREATE EXTENSION IF NOT EXISTS unaccent;
EOSQL
        if [ "${PG_MAJOR:-0}" -ge 13 ]; then
            psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_ODOO_DB" <<-EOSQL
            CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
        fi
    fi
fi
