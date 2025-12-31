# Disaster Recovery Runbook

## Overview
This document outlines the procedures for backing up and restoring the Amber system data. The system relies on the following stateful components:
- **Postgres**: Stores relational metadata (Tenants, Users, Document references).
- **Neo4j**: Stores the knowledge graph (Entities, Relationships).
- **MinIO**: Stores raw documents and Milvus vector data.
- **Milvus**: Stores vector embeddings (Data persisted in MinIO/Etcd).

## Backup Procedure

### Automated Backup
Run the backup script to create a timestamped backup of all components.

```bash
./scripts/backup.sh
```

**Output Location**: `./backups/YYYYMMDD_HHMMSS/`
**Contents**:
- `postgres.sql`: Logical dump of Postgres database.
- `neo4j.cypher`: Logical Cypher export of Neo4j graph.
- `minio_data.tar.gz`: Compressed archive of MinIO data volume.
- `uploads.tar.gz`: Compressed archive of local uploads directory.

### Manual Verification
After backup, verify the contents:
```bash
ls -lh ./backups/<timestamp>/
```
Ensure files are non-empty.

## Restore Procedure

> [!WARNING]
> Restoring will **OVERWRITE** existing data in the containers. Ensure you have a backup of the current state if effective data exists.

### Full System Restore
1. Stop the application (optional but recommended to prevent writes).
2. Ensure database services (`postgres`, `neo4j`, `minio`) are running.
3. Run the restore script:

```bash
./scripts/restore.sh ./backups/YYYYMMDD_HHMMSS
```

4. You will be prompted to confirm. Type `y`.
5. Restart services to ensure volume changes are picked up correctly (especially for MinIO/Milvus).

```bash
docker-compose restart
```

### Partial Restore
If you only need to restore specific components, you can manually run the commands found in `scripts/restore.sh` for the specific service.

## Troubleshooting

- **Neo4j Restore Fails**: Ensure APOC plugin is enabled and `apoc.export.*` settings are configured in `docker-compose.yml`.
- **MinIO/Milvus Inconsistency**: If vectors are missing after restore, ensure both `minio_data.tar.gz` was restored AND `etcd` volume matches. *Note: Current script backs up MinIO data but not Etcd directly. For full Milvus DR, it is recommended to stop the stack and backup all volumes, but MinIO restore often suffices for data recovery if Etcd is rebuilt (though indexing might need regeneration).*
- **Permission Errors**: Ensure the script is run with user permissions that can access Docker.
