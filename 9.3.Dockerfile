FROM docker.io/library/postgres:9.3-alpine AS builder

SHELL ["/bin/sh", "-e", "-c"]

ARG TARGETARCH \
    GO_VERSION="1.26.1" \
    PG_BACKREST_VERSION="2.48"

ENV PATH="$PATH:/usr/local/go/bin"

# Install System Dependencies
RUN apk add --no-cache --virtual .build-deps \
        build-base cmake git yaml-dev zlib-dev \
        libxml2-dev postgresql-dev bzip2-dev \
        readline-dev tar && \
    mkdir -p /builds

WORKDIR /tmp

# Install Go
RUN wget -qO go.tar.gz https://go.dev/dl/go${GO_VERSION}.linux-${TARGETARCH}.tar.gz && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz

# Build Restic
RUN git clone --depth 1 https://github.com/restic/restic && \
    cd restic && go run build.go && mv restic /builds/ && rm -rf /tmp/restic

# Build Rclone
RUN git clone --depth 1 https://github.com/rclone/rclone && \
    cd rclone && go build -o /builds/rclone && rm -rf /tmp/rclone

# Build pgBackRest
RUN git clone -b release/${PG_BACKREST_VERSION} --depth 1 https://github.com/pgbackrest/pgbackrest && \
    cd pgbackrest/src && ./configure && make && mv pgbackrest /builds/ && rm -rf /tmp/pgbackrest

# Build unaccent extension
RUN wget -qO postgresql.tar.bz2 https://ftp.postgresql.org/pub/source/v9.3.25/postgresql-9.3.25.tar.bz2 && \
    tar -xjf postgresql.tar.bz2 && \
    cd postgresql-9.3.25/contrib/unaccent && \
    make USE_PGXS=1 && make USE_PGXS=1 install && \
    rm -rf /tmp/postgresql-9.3.25*

### RUNTIME ###
FROM docker.io/library/postgres:9.3-alpine

SHELL ["/bin/sh", "-e", "-c"]

COPY --from=builder --chown=postgres:postgres /builds/pgbackrest /usr/local/bin/
COPY --from=builder --chown=postgres:postgres /builds/restic     /usr/local/bin/
COPY --from=builder --chown=postgres:postgres /builds/rclone    /usr/local/bin/

RUN apk add --no-cache libbz2 python3 && \
    apk add --no-cache --virtual .build-deps curl py3-pip && \
    pip3 install --no-cache-dir apprise && \
    curl -sfL https://raw.githubusercontent.com/creativeprojects/resticprofile/master/install.sh | sh -s -- -b /usr/local/bin && \
    apk del .build-deps

COPY --from=builder --chown=postgres:postgres /usr/local/lib/postgresql/unaccent.so /usr/local/lib/postgresql/
COPY --from=builder --chown=postgres:postgres /usr/local/share/postgresql/extension/unaccent* /usr/local/share/postgresql/extension/

COPY --chown=postgres:postgres files/init/common/* /docker-entrypoint-initdb.d/
COPY --chown=postgres:postgres tools/moouro_backup.py /usr/local/sbin/moouro_backup
COPY --chown=postgres:postgres tools/moouro_restore.py /usr/local/sbin/moouro_restore
COPY --chown=postgres:postgres tools/moouro_check.py /usr/local/sbin/moouro_check
COPY --chown=postgres:postgres tools/moouro_list.py /usr/local/sbin/moouro_list
COPY --chown=postgres:postgres moouro-entrypoint.sh /moouro-entrypoint.sh

RUN mkdir -p /var/log/pgbackrest && \
    chown postgres:postgres /var/log/pgbackrest && \
    chmod +x /usr/local/sbin/moouro_* /moouro-entrypoint.sh

# Smoke Tests
RUN pgbackrest version && restic version && resticprofile version && rclone version && apprise --version

USER postgres
ENTRYPOINT ["/moouro-entrypoint.sh"]
