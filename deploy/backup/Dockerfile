# syntax=docker/dockerfile:1
# Image de sauvegarde AH2 : restic (depot LOCAL chiffre) + pg_dump 17 + ssh (envoi SFTP
# hebdomadaire) + supercronic (planification). Contexte de build : deploy/backup.
#   docker build -t ghcr.io/<GHCR_OWNER>/ah2-backup:<tag> deploy/backup
#
# Utilisateur : uid/gid 10001, le MEME que l'API (deploy/Dockerfile.api). Les volumes
# uploads / product_photos / consents appartiennent a 10001 : le service les lit donc sans
# etre root, meme montes en lecture seule. Le depot restic (dossier hote /srv/ah2-backups)
# doit appartenir a 10001 aussi (voir docs/exploitation/sauvegardes.md).

# --- Etape 1 : telechargements verifies (curl et bzip2 ne restent pas dans l'image finale)
FROM alpine:3.22 AS fetch
# Memes version et empreinte que deploy/Dockerfile.api (supercronic v0.2.51)
ARG SUPERCRONIC_VERSION=v0.2.51
ARG SUPERCRONIC_SHA256=cc232108374e8e2b537045f2d5eaa1229f619db314c3ba6a14d38b35dc0aa123
# restic : empreinte du fichier SHA256SUMS de la release v0.19.1 (github.com/restic/restic)
ARG RESTIC_VERSION=0.19.1
ARG RESTIC_SHA256=f415415624dcc452f2a02b8c33641791a8c6d6d3b65bbb3543fcf9a25151585c
RUN apk add --no-cache curl bzip2 \
 && curl -fsSL -o /supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
 && echo "${SUPERCRONIC_SHA256}  /supercronic" | sha256sum -c - \
 && curl -fsSL -o /restic.bz2 \
      "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" \
 && echo "${RESTIC_SHA256}  /restic.bz2" | sha256sum -c - \
 && bunzip2 /restic.bz2 \
 && chmod 0755 /supercronic /restic

# --- Etape 2 : image finale
FROM alpine:3.22

ENV TZ=Africa/Douala \
    RESTIC_CACHE_DIR=/var/cache/restic \
    RESTIC_REPOSITORY=/backups/repo \
    STATUS_DIR=/var/lib/ah2-status \
    GOMEMLIMIT=180MiB

# postgresql17-client : meme version majeure que l'image db (postgres 17.x).
RUN apk add --no-cache bash tzdata postgresql17-client openssh-client-default jq flock \
 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
 && addgroup -g 10001 backup \
 && adduser -D -u 10001 -G backup -h /home/backup -s /sbin/nologin backup \
 && mkdir -p /backups/repo /var/lib/ah2-status /var/cache/restic /var/tmp/ah2-stage \
             /home/backup/.ssh /data/uploads /data/product_photos /data/consents \
 && chown -R 10001:10001 /backups /var/lib/ah2-status /var/cache/restic /var/tmp/ah2-stage /home/backup \
 && chmod 0700 /home/backup/.ssh

COPY --from=fetch /supercronic /usr/local/bin/supercronic
COPY --from=fetch /restic /usr/local/bin/restic
COPY --chown=10001:10001 lib.sh entrypoint.sh hourly.sh nightly.sh offsite.sh pull_prepare.sh restore.sh verify.sh crontab /opt/backup/
RUN chmod 0755 /opt/backup/*.sh

USER 10001:10001
WORKDIR /home/backup
ENTRYPOINT ["/opt/backup/entrypoint.sh"]
