ARG MONGO_IMAGE_TAG=7
FROM mongo:${MONGO_IMAGE_TAG}

COPY backup-loop.sh /scripts/backup-loop.sh
RUN chmod +x /scripts/backup-loop.sh

ENTRYPOINT ["/bin/sh", "/scripts/backup-loop.sh"]
