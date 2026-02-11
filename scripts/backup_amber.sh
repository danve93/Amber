#!/bin/bash
set -e

BACKUP_DIR="$(pwd)/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

VOLUMES=(
    "amber_graphrag-postgres"
    "amber_graphrag-neo4j"
    "amber_graphrag-milvus"
    "amber_graphrag-etcd"
    "amber_graphrag-minio"
    "amber_graphrag-redis"
    "amber_graphrag-uploads"
    "amber_neo4j_data"
    "amber_neo4j_logs"
    "amber_neo4j_plugins"
    "amber_postgres_trulens_data"
)

echo "Starting backup to $BACKUP_DIR..."

for VOLUME in "${VOLUMES[@]}"; do
    if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
        echo "Backing up $VOLUME..."
        docker run --rm \
            -v "$VOLUME":/volume \
            -v "$BACKUP_DIR":/backup \
            alpine tar -czf "/backup/${VOLUME}_${TIMESTAMP}.tar.gz" -C /volume .
    else
        echo "Warning: Volume $VOLUME not found, skipping."
    fi
done

echo "Backup complete!"
ls -lh "$BACKUP_DIR"
