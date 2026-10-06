<h1 align="center">
  <img src="moouro.png" />
  <div>Moouro - Container Image</div>

  [![Tests](https://github.com/GrupoIsonor/moouro/actions/workflows/moouro.yml/badge.svg)](https://github.com/GrupoIsonor/moouro/actions/workflows/moouro.yml)
</h1>

<p align="center">
*** PROJECT UNDER DEVELOPMENT. NOT READY FOR PRODUCTION ***

Database and Filestore Management for Odoo environments
</p>
<p align="center">
  -- <a href="https://www.grupoisonor.es/">Grupo Isonor</a> --
</p>

---

## Overview

Moouro extends the official `postgres:<version>-alpine` image so that an Odoo deployment gets its **database backups, filestore backups, notifications and replication** from a single container.

| Included | Purpose |
|----------|---------|
| [pgBackRest](https://pgbackrest.org/) | WAL-based PostgreSQL backups and Point-in-Time Recovery (PITR) |
| [restic](https://github.com/restic/restic) + [resticprofile](https://github.com/creativeprojects/resticprofile) | Filestore backups |
| [rclone](https://rclone.org/) | Extra storage backends for restic |
| [apprise](https://github.com/caronc/apprise) | Push notifications |
| `unaccent`, `vector` (PostgreSQL 13+) | Extensions required by Odoo / AI features |
| Streaming replication | Replica setup with `moouro_init_replica` |
| [Patroni](https://github.com/patroni/patroni) (etcd3) | High availability, only in the Patroni flavor |

Supported PostgreSQL versions: `9.6` and `10` – `18`.

## Image flavors

Two flavors are published per PostgreSQL version at `ghcr.io/grupoisonor/moouro`:

| Flavor | Tags | Description |
|--------|------|-------------|
| **runtime** | `18`, `latest` | PostgreSQL plus all the tools above. Starts `postgres` through `moouro-entrypoint`. |
| **runtime + Patroni (etcd3)** | `18-patroni-etcd3`, `latest-patroni-etcd3` | The runtime flavor plus Patroni. Starts `patroni /etc/patroni/config.yml` as the `postgres` user and bypasses `moouro-entrypoint`, so the automatic pgBackRest/resticprofile initialization does not run. |

`latest` and `latest-patroni-etcd3` point to PostgreSQL 18. Replace `18` with any supported version.

For a Patroni example, see [`compose.patroni.yaml`](tests/data/project_demo/compose.patroni.yaml) and [`patroni1.yaml`](tests/data/project_demo/config/patroni1.yaml).

## Quick start

Minimal project layout:

```
myproject/
├── compose.yaml
├── secrets/
│   ├── backup_password.txt
│   ├── odoo_db_password.txt
│   └── postgres_db_password.txt
└── config/
    ├── apprise.yaml
    ├── pgbackrest.conf
    ├── postgresql.conf
    └── resticprofile.yaml
```

`compose.yaml`:

```yml
services:
  db:
    image: ghcr.io/grupoisonor/moouro:18
    environment:
      POSTGRES_DB: odoodb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_db_password
      POSTGRES_ODOO_USER: odoo
      POSTGRES_ODOO_PASSWORD_FILE: /run/secrets/odoo_db_password
      POSTGRES_ODOO_DB: odoodb
      POSTGRES_INITDB_ARGS: --locale=C --encoding=UTF8
    volumes:
      - ./config/pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro,Z
      - ./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro,Z
      - ./config/resticprofile.yaml:/etc/resticprofile/profiles.yaml:ro,Z
      - ./config/apprise.yaml:/etc/apprise/apprise.yaml:ro,Z
      - filestore:/var/lib/odoo/data
      - db:/var/lib/postgresql
    secrets:
      - backup_password
      - postgres_db_password
      - odoo_db_password
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    hostname: odoo-db
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo -d odoodb"]
      interval: 10s
      timeout: 5s
      retries: 15
      start_period: 30s

  odoo:
    image: isodoo:my-custom-image-19
    depends_on:
      db:
        condition: service_healthy
    ports:
      - '127.0.0.1:8069:8069'
    secrets:
      - odoo_db_password
    environment:
      OCONF__options__log_level: debug
      OCONF__options__db_filter: odoodb$
      OCONF__options__db_user: odoo
      FOCONF__options__db_password: /run/secrets/odoo_db_password
      OCONF__options__db_host: odoo-db
      OCONF__options__db_name: odoodb
      OCONF__options__proxy_mode: false
      OCONF__options__workers: 0
      OCONF__options__max_cron_threads: 0
      OCONF__options__without_demo: all
    volumes:
      - filestore:/var/lib/odoo/data
    hostname: odoo


secrets:
  backup_password:
    x-podman.relabel: Z
    file: ./secrets/backup_password.txt
  postgres_db_password:
    x-podman.relabel: Z
    file: ./secrets/postgres_db_password.txt
  odoo_db_password:
    x-podman.relabel: Z
    file: ./secrets/odoo_db_password.txt

volumes:
  filestore:
  db:
```

## Configuration

### External documentation

- pgBackRest: https://pgbackrest.org/configuration.html
- ResticProfile: https://creativeprojects.github.io/resticprofile/configuration/getting_started/index.html
- Apprise: https://appriseit.com/getting-started/configuration

You can also get inspiration from the configurations used in the tests: https://github.com/GrupoIsonor/moouro/tree/master/tests/data/project_demo/config

### Database backup (pgBackRest)

When using pgBackRest, the stanza must be named `main`.
`archive_mode` must be enabled in PostgreSQL.

- If `/etc/pgbackrest/pgbackrest.conf` is not present, pgBackRest will not be initialized.

### Filestore backup (ResticProfile + Restic + RClone)

The image uses ResticProfile for filestore backups.

- Use of scheduled backups via resticprofile is not available (can use an external solution).
- If `/etc/resticprofile/profiles.yaml` is not present, ResticProfile will not be initialized.

### Environment variables

All environment variables supported by the official PostgreSQL Docker image are available:
[https://hub.docker.com/_/postgres#environment-variables](https://hub.docker.com/_/postgres#environment-variables)

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| POSTGRES_ODOO_USER | The username for odoo user | Yes | "" |
| POSTGRES_ODOO_PASSWORD | The password for odoo user | Yes | "" |
| POSTGRES_ODOO_DB | The database for odoo user | No | "" |
| POSTGRES_REPLICATOR_USER | The name for the 'replicator' role | No | replicator |
| POSTGRES_REPLICATOR_PASSWORD | The password for 'replicator' role. If it is not specified, the role will not be created. | No | "" |

> Passwords can be read from a file with the `_FILE` suffix, e.g. `POSTGRES_ODOO_PASSWORD_FILE`.

### Environment variables (replication mode)

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| POSTGRES_REPLICATION | Enables replication | No | false |
| POSTGRES_MASTER_HOST | The master host | No | "" |
| POSTGRES_MASTER_PORT | The master host port | No | "" |
| POSTGRES_MASTER_REPLICATOR_USER | The name for the master 'replicator' role | No | replicator |
| POSTGRES_MASTER_REPLICATOR_PASSWORD_FILE | The password for master 'replicator' role | No | "" |

### Configuration file paths

| Path | Description |
| ---- | ----------- |
| /etc/pgbackrest/pgbackrest.conf | pgBackRest configuration |
| /etc/postgresql/postgresql.conf | Postgres configuration |
| /etc/resticprofile/profiles.yaml | ResticProfile configuration |
| /etc/apprise/apprise.yaml | Apprise configuration |

## Scripts

These scripts are available to help you get started with the tools.
It is highly recommended that you learn how to use pgBackRest and ResticProfile by consulting their respective documentation.

- `moouro_backup` – Execute pgBackRest and Restic backups

  Syntax: `moouro_backup <full|incr> [dry-run] [--notify]`

  Examples:
  ```sh
    moouro_backup full                  # normal backup
    moouro_backup incr                  # incremental backup
    moouro_backup full dry-run          # dry run (no changes)
    moouro_backup full --notify         # with notification
    moouro_backup incr dry-run --notify # combined
  ```

- `moouro_restore` – Restore pgBackRest and Restic backups.

  Syntax: `moouro_restore <destination> <pgBackrest_date|latest> <restic_snapshot_id|latest> [dry-run]`

  WARNING: This restore script is very aggressive. It will overwrite all data and discard any unwritten changes available in the WAL.

  Example:
  ```sh
    moouro_restore /var/lib/odoo/data latest latest
    moouro_restore /var/lib/odoo/data 2026-04-08 abc123def
    moouro_restore /var/lib/odoo/data 2026-04-08 abc123def dry-run
  ```

- `moouro_check` – Run pgBackRest and Restic checks

  Syntax: `moouro_check [--notify]`

  Example:
  ```sh
    moouro_check
    moouro_check --notify
  ```

- `moouro_list` – List available restore points

  Syntax: `moouro_list`

  Example:
  ```sh
    moouro_list
  ```

- `moouro_init_replica` – Launch pg_basebackup to start the replica. It should be called only once, when the database is empty.

  Syntax: `moouro_init_replica`

  Example:
  ```sh
    moouro_init_replica
  ```

## FAQ

- How to use scripts?

  Example with `docker`:
  - With psql running:
    ```docker compose exec -u postgres db moouro_backup full```
  - Without psql running:
    ```docker compose run --rm --entrypoint /bin/sh -u postgres db -c 'moouro_restore /var/lib/odoo/data latest latest'```

- I've already initialized the database, but I want to add new backup profile. What should I do?

  Simply add the profile to the pgbackrest and resticprofile configuration files. Moouro attempts to initialize the profiles every time it starts up.
