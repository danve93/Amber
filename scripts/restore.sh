#!/bin/bash
set -e

# Usage: ./scripts/restore.sh <backup_timestamp_dir>

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_directory_path>"
    exit 1
fi

BACKUP_PATH="$1"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Error: Directory $BACKUP_PATH does not exist."
    exit 1
fi

POSTGRES_CONTAINER="graphrag-postgres"
NEO4J_CONTAINER="graphrag-neo4j"
MINIO_VOLUME="graphrag-minio"
UPLOADS_VOLUME="graphrag-uploads"

echo "Starting restore from $BACKUP_PATH..."

read -p "WARNING: This will overwrite current data. Are you sure? (y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Restore cancelled."
    exit 1
fi

# 1. Postgres Restore
if [ -f "$BACKUP_PATH/postgres.sql" ]; then
    echo "Restoring Postgres..."
    # Drop and recreate schema to be clean (or just rely on clean script)
    # Here we just pipe psql. Might need to terminate connections first if active.
    cat "$BACKUP_PATH/postgres.sql" | docker exec -i "$POSTGRES_CONTAINER" psql -U graphrag -d graphrag
else
    echo "Warning: postgres.sql not found in backup."
fi

# 2. Neo4j Restore
if [ -f "$BACKUP_PATH/neo4j.cypher" ]; then
    echo "Restoring Neo4j..."
    # Clear existing data first
    docker exec "$NEO4J_CONTAINER" cypher-shell -u neo4j -p graphrag123 "MATCH (n) DETACH DELETE n"
    
    # Import cypher
    cat "$BACKUP_PATH/neo4j.cypher" | docker exec -i "$NEO4J_CONTAINER" cypher-shell -u neo4j -p graphrag123
else
    echo "Warning: neo4j.cypher not found in backup."
fi

# 3. MinIO Restore
if [ -f "$BACKUP_PATH/minio_data.tar.gz" ]; then
    echo "Restoring MinIO volume..."
    # We clear the volume first? 
    # To be safe, we just extract over.
    docker run --rm \
        -v "$MINIO_VOLUME":/data \
        -v "$(realpath $BACKUP_PATH)":/backup \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/minio_data.tar.gz -C /data"
else
    echo "Warning: minio_data.tar.gz not found in backup."
fi

# 4. Uploads Restore
if [ -f "$BACKUP_PATH/uploads.tar.gz" ]; then
    echo "Restoring Uploads volume..."
    docker run --rm \
        -v "$UPLOADS_VOLUME":/data \
        -v "$(realpath $BACKUP_PATH)":/backup \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/uploads.tar.gz -C /data"
else
    echo "Warning: uploads.tar.gz not found in backup."
fi

echo "Restore completed. You may need to restart services to reflect volume changes (especially MinIO)."
