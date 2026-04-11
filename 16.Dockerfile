FROM docker.io/library/postgres:16-alpine AS pgvector-builder

SHELL ["/bin/sh", "-e", "-c"]

RUN apk add --no-cache git build-base clang19 llvm19 llvm19-linker-tools llvm19-dev

WORKDIR /tmp

RUN git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    make && \
    make install


FROM docker.io/library/postgres:16-alpine AS runtime

SHELL ["/bin/sh", "-e", "-c"]

COPY --from=pgvector-builder --chown=postgres:postgres /usr/local/lib/postgresql/bitcode/vector.index.bc /usr/local/lib/postgresql/bitcode/vector.index.bc
COPY --from=pgvector-builder --chown=postgres:postgres /usr/local/lib/postgresql/vector.so /usr/local/lib/postgresql/vector.so
COPY --from=pgvector-builder --chown=postgres:postgres /usr/local/share/postgresql/extension /usr/local/share/postgresql/extension

RUN apk add --no-cache pgbackrest restic rclone python3 apprise && \
    apk add --no-cache --virtual .build-deps curl && \
    curl -sfL https://raw.githubusercontent.com/creativeprojects/resticprofile/master/install.sh | sh -s -- -b /usr/local/bin && \
    apk del .build-deps

COPY --chown=postgres:postgres files/init/common/* /docker-entrypoint-initdb.d/
COPY --chown=postgres:postgres files/init/ai/* /docker-entrypoint-initdb.d/
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
