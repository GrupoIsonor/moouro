FROM docker.io/library/postgres:9.6-alpine AS runtime

SHELL ["/bin/sh", "-e", "-c"]

RUN apk add --no-cache pgbackrest restic rclone python3 && \
    apk add --no-cache --virtual .build-deps curl py3-pip && \
    pip3 install --no-cache-dir apprise && \
    curl -sfL https://raw.githubusercontent.com/creativeprojects/resticprofile/master/install.sh | sh -s -- -b /usr/local/bin && \
    apk del .build-deps

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
