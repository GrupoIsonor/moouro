<h1 align="center">
  <img src="moouro.png" />
  <div>Moouro - Docker Image</div>

  [![Tests](https://github.com/GrupoIsonor/moouro/actions/workflows/moouro.yml/badge.svg)](https://github.com/GrupoIsonor/moouro/actions/workflows/moouro.yml)
</h1>

<p align="center">
*** PROJECT UNDER DEVELOPMENT. NOT READY FOR PRODUCTION ***
<p align="center">
Database and Filestore Management for Odoo environments
(By Grupo Isonor)
</p>

---

## Features

- unaccent PostgreSQL extension
- vector (13+) PostgreSQL extension
- Point-in-Time Recovery (PITR)
- No Package Manager
- [pgBackRest](https://pgbackrest.org/) – PostgreSQL backups
- [restic](https://github.com/restic/restic) – Filestore backups
- [resticprofile](https://github.com/creativeprojects/resticprofile) – Restic profile management
- [rclone](https://rclone.org/) – Extended storage support for restic
- [apprise](https://github.com/caronc/apprise) – Push notifications

## Documentation

- pgBackRest: https://pgbackrest.org/configuration.html
- ResticProfile: https://creativeprojects.github.io/resticprofile/configuration/getting_started/index.html
- AppRise: https://appriseit.com/getting-started/configuration

You can also get inspiration from the configurations used in the tests: https://github.com/GrupoIsonor/moouro/tree/master/tests/data/project_demo/config

### Database Backup (pgBackRest)

When using pgBackRest, the stanza must be named `main`.
`archive_mode` must be enabled in PostgreSQL.

- If `/etc/pgbackrest/pgbackrest.conf` is not present, pgBackRest will not be initialized.

### Filestore Backup (ResticProfile + Restic + RClone)

The image uses ResticProfile for filestore backups.

- Use of scheduled backups via resticprofile is not available (can use an external solution).
- If `/etc/resticprofile/profiles.yaml` is not present, ResticProfile will not be initialized.

### Environment Variables

All environment variables supported by the official PostgreSQL Docker image are available:
[https://hub.docker.com/_/postgres#environment-variables](https://hub.docker.com/_/postgres#environment-variables)

| Name | Description | Required |
| ---- | ----------- | -------- |
| POSTGRES_ODOO_USER | The username for odoo user | Yes |
| POSTGRES_ODOO_PASSWORD | The password for odoo user | Yes |
| POSTGRES_ODOO_DB | The database for odoo user | No |

### Points Of Interest

| Path | Description |
| ---- | ----------- |
| /etc/pgbackrest/pgbackrest.conf | pbBackRest configuration |
| /etc/postgresql/postgresql.conf | Postgres configuration |
| /etc/resticprofile/profiles.yaml | ResticProfile configuration |
| /etc/apprise/apprise.yaml | AppRise configuration |

### Scripts

These scripts are available to help you get started with the tools.
It is highly recommend that you learn how to use pgBackRest and ResticProfile by consulting their respective documentation.

- `moouro_backup` – Execute pgBackRest and Restic backups

  Syntaxis: `moouro_backup <full|incr> [dry-run] [--notify]`

  Examples:
  ```sh
    moouro_backup full                  # normal backup
    moouro_backup incr                  # incremental backup
    moouro_backup full dry-run          # dry run (no changes)
    moouro_backup full --notify         # with notification
    moouro_backup incr dry-run --notify # combined
  ```

- `moouro_restore` – Restore pgBackRest and Restic backups.

  Syntaxis: `moouro_restore <destination> <pgBackrest_date|latest> <restic_snapshot_id|latest> [dry-run]`

  WARNING: This restore script is very aggressive. It will overwrite all data and discard any unwritten changes available in the WAL.

  Example:
  ```sh
    moouro_restore /var/lib/odoo/filestore latest latest
    moouro_restore /var/lib/odoo/filestore 2026-04-08 abc123def
    moouro_restore /var/lib/odoo/filestore 2026-04-08 abc123def dry-run
  ```

- `moouro_check` – Run pgBackRest and Restic checks

  Syntaxis: `moouro_check [--notify]`

  Example:
  ```sh
    moouro_check
    moouro_check --notify
  ```

- `moouro_list` – List available restore points

  Syntaxis: `moouro_list`

  Example:
  ```sh
    moouro_list
  ```

### FAQ

- How to use scripts?

  Example with `docker`:
  - With psql running:
    ```docker compose exec moouro_backup full```
  - Without psql running:
    ```docker compose run --rm --entrypoint /bin/ash moouro -c 'moouro_restore /var/lib/odoo/data'```

- I've already initialized the database, but I want to add new backup profile. What should I do?

  Simply add the profile to the pgbackrest and resticprofile configuration files. Moouro attempts to initialize the profiles every time it starts up.


---
<div align="center"><h2>Very Basic Usage Example</h2></div>

### Folder Tree
```
myproject/
  - docker-compose.yaml
  - secrets/
    - restic_password.txt
  - config/
    - apprise.yaml
    - pgbackrest.conf
    - postgresql.conf
    - resticprofile.yaml
```

### docker-compose.yaml
```yml
services:
  db:
    image: ghcr.io/grupoisonor/moouro:18
    user: postgres
    environment:
      POSTGRES_DB: odoodb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_ODOO_USER: odoo
      POSTGRES_ODOO_PASSWORD: odoo
      POSTGRES_ODOO_DB: odoodb
      POSTGRES_INITDB_ARGS: --locale=C --encoding=UTF8
    volumes:
      - ./pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:z
      - ./postgresql.conf:/etc/postgresql/postgresql.conf:z
      - ./resticprofile.yaml:/etc/resticprofile/profiles.yaml:z
      - ./apprise.yaml:/etc/apprise/apprise.yaml:z
      - filestore:/var/lib/odoo/data
      - db:/var/lib/postgresql
    secrets:
      - restic_password
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    hostname: odoo-db
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo -d odoodb"]
      interval: 10s
      timeout: 5s
      retries: 15
      start_period: 30s

  odoo:
    image: localhost/isodoo:my-custom-image-19
    pull_policy: never
    user: odoo
    depends_on:
      db:
        condition: service_healthy
    ports:
      - '127.0.0.1:8069:8069'
    environment:
      OCONF__options__log_level: debug
      OCONF__options__db_filter: odoodb$
      OCONF__options__db_user: odoo
      OCONF__options__db_password: odoo
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
  restic_password:
    file: ./secrets/restic_password.txt

volumes:
  filestore:
  db:
```
