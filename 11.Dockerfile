FROM docker.io/library/postgres:11-alpine AS runtime

SHELL ["/bin/ash", "-eo", "pipefail", "-c"]

RUN apk add --no-cache pgbackrest restic rclone python3 py3-pip tzdata musl-locales && \
    apk add --no-cache --virtual .build-deps curl && \
    pip3 install --no-cache-dir --break-system-packages apprise && \
    curl -sfL https://raw.githubusercontent.com/creativeprojects/resticprofile/master/install.sh | sh -s -- -b /usr/local/bin && \
    apk del .build-deps && \
    rm -rf /etc/pgbackrest

COPY --chown=postgres:postgres moouro-entrypoint.sh /usr/local/bin/moouro-entrypoint
COPY --chown=postgres:postgres files/init/common/* /docker-entrypoint-initdb.d/
COPY --chown=postgres:postgres tools/moouro_backup.py /usr/local/sbin/moouro_backup
COPY --chown=postgres:postgres tools/moouro_restore.py /usr/local/sbin/moouro_restore
COPY --chown=postgres:postgres tools/moouro_check.py /usr/local/sbin/moouro_check
COPY --chown=postgres:postgres tools/moouro_list.py /usr/local/sbin/moouro_list
COPY --chown=postgres:postgres tools/moouro_init_replica.sh /usr/local/sbin/moouro_init_replica

RUN mkdir -p /var/log/pgbackrest && \
    chown postgres:postgres /var/log/pgbackrest && \
    chmod 750 /usr/local/sbin/moouro_* && \
    chmod +x /usr/local/bin/moouro-entrypoint /usr/local/sbin/moouro_init_replica

# Smoke Tests
RUN pgbackrest version && restic version && resticprofile version && rclone version && apprise --version

ENTRYPOINT ["/usr/local/bin/moouro-entrypoint"]
CMD ["postgres"]


FROM runtime AS runtime-patroni-etcd3

WORKDIR /opt/patroni

RUN apk add --no-cache gosu && \
    apk add --no-cache --virtual .build-deps py3-pip build-base linux-headers python3-dev && \
    python3 -m venv . && \
    ./bin/pip install --no-cache-dir "patroni[psycopg3,etcd3]" && \
    apk del .build-deps

# Smoke test
RUN /opt/patroni/bin/patroni --version

ENV PATH="/opt/patroni/bin:$PATH"

ENTRYPOINT ["gosu", "postgres"]
CMD ["patroni", "/etc/patroni/config.yml"]
