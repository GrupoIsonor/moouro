#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER ${POSTGRES_ODOO_USER} WITH PASSWORD '${POSTGRES_ODOO_PASSWORD}';
    ALTER USER ${POSTGRES_ODOO_USER} CREATEDB;
EOSQL

if [ -n "${POSTGRES_ODOO_DB:-}" ]; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c \
        "CREATE DATABASE ${POSTGRES_ODOO_DB}
         WITH OWNER = ${POSTGRES_ODOO_USER}
         ENCODING = 'UTF8'
         LC_COLLATE = 'C'
         LC_CTYPE = 'C'
         TEMPLATE = template0;"
fi
