FROM alpine:latest

SHELL ["/bin/sh", "-eo", "pipefail", "-c"]

RUN set -eux; \
    addgroup --gid 7777 --system isodoo; \
    adduser \
        --disabled-password \
        --no-create-home \
        --ingroup isodoo \
        --no-create-home \
        --system \
        --uid 7777 \
        isodoo; \
    mkdir /var/lib/pgbackrest; \
    chown isodoo:isodoo /var/lib/pgbackrest;

RUN set -eux; \
    apk add --no-cache --virtual backup-tools \
        pgbackrest \
        restic \
        rclone;

COPY --chown=isodoo:isodoo tools/backup.py /usr/local/sbin/backup

USER isodoo
