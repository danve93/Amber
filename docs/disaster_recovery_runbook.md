# Disaster Recovery Runbook

<!-- markdownlint-disable MD013 -->

## Overview

This document outlines the procedures for backing up and restoring the Amber
system data. The system relies on the following stateful components:

- **Postgres**: Stores relational metadata (Tenants, Users, Document
  references).
- **Neo4j**: Stores the knowledge graph (Entities, Relationships).
- **MinIO**: Current/legacy S3-compatible storage for raw documents and Milvus
  object data.
- **SeaweedFS**: Target S3-compatible storage during MinIO migration and after
  cutover.
- **Milvus**: Stores vector embeddings (data persisted in object storage and
  Etcd).

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
- `seaweed_data.tar.gz` (optional during migration): Compressed archive of
  SeaweedFS data volume.
- `uploads.tar.gz`: Compressed archive of local uploads directory.

### Migration Mode (MinIO -> SeaweedFS)

When both storages are running in parallel:

- Treat **MinIO as source of truth** until production cutover is complete.
- Run periodic object manifests for both endpoints and compare before cutover.
- Keep MinIO online for rollback until reconciliation remains clean for the
  defined rollback window.

### Migration Verification Commands

Use the migration helpers to sync and validate object parity:

```bash
# 1) Source manifest (MinIO)
python3 scripts/storage_manifest.py \
  --endpoint localhost:9000 \
  --access-key "$MINIO_ROOT_USER" \
  --secret-key "$MINIO_ROOT_PASSWORD" \
  --out /tmp/minio-manifest.jsonl

# 2) Copy source -> destination (idempotent, can be re-run)
bash scripts/storage_sync.sh \
  --src-endpoint localhost:9000 \
  --src-access "$MINIO_ROOT_USER" \
  --src-secret "$MINIO_ROOT_PASSWORD" \
  --dst-endpoint localhost:8333 \
  --dst-access "$OBJECT_STORAGE_ACCESS_KEY" \
  --dst-secret "$OBJECT_STORAGE_SECRET_KEY"

# 3) Destination manifest (SeaweedFS)
python3 scripts/storage_manifest.py \
  --endpoint localhost:8333 \
  --access-key "$OBJECT_STORAGE_ACCESS_KEY" \
  --secret-key "$OBJECT_STORAGE_SECRET_KEY" \
  --out /tmp/seaweed-manifest.jsonl

# 4) Drift report (exit code 1 if mismatch/missing/extra)
python3 scripts/storage_compare.py \
  --src /tmp/minio-manifest.jsonl \
  --dst /tmp/seaweed-manifest.jsonl
```

### Production Cutover (Write Freeze Required)

1. Take a fresh snapshot with `./scripts/backup.sh`.
2. Enter write freeze by stopping writers:
   - `docker compose stop api worker`
   - `docker compose stop milvus`
3. Run one final sync and manifest compare (`missing=0`, `mismatched=0` are
   mandatory).
4. Switch runtime endpoints:
   - App/worker: `OBJECT_STORAGE_HOST/PORT/ACCESS_KEY/SECRET_KEY` -> SeaweedFS
   - Milvus: `MINIO_ADDRESS=seaweed-s3:8333` with matching credentials
5. Restart in order:
   - `docker compose up -d seaweed-master seaweed-volume seaweed-filer seaweed-s3`
   - `docker compose up -d milvus`
   - `docker compose up -d api worker`
6. Run smoke checks (upload/download, query flow, export, backup).

If any gate fails, rollback immediately (see below).

### Rollback Procedure (Post-Cutover)

1. Stop writers and Milvus:
   - `docker compose stop api worker milvus`
2. Repoint app/worker + Milvus storage settings back to MinIO.
3. Start services:
   - `docker compose up -d minio milvus api worker`
4. Confirm upload/download and query flow before reopening traffic.

### Rollback Window and Decommission

- Keep MinIO online in read-only/standby mode for **7-14 days** after cutover.
- Run daily manifest reconciliation (`storage_manifest.py` + `storage_compare.py`).
- Decommission MinIO only after rollback window completes with zero drift.

### Automated Daily Reconciliation + Tidy

Use the maintenance wrapper to run reconciliation and Seaweed test-bucket tidy
in one command:

```bash
bash scripts/seaweed_reconcile_tidy.sh --apply-tidy
```

If you want automatic healing when drift is detected, enable auto-sync:

```bash
bash scripts/seaweed_reconcile_tidy.sh --auto-sync --apply-tidy
```

Example cron (daily at 02:15 UTC, logs to `/var/log/amber`):

```cron
15 2 * * * cd /home/daniele/Amber_2.0 && \
  bash scripts/seaweed_reconcile_tidy.sh --auto-sync --apply-tidy \
  >> /var/log/amber/seaweed-maintenance.log 2>&1
```

### Manual Verification

After backup, verify the contents:

```bash
ls -lh ./backups/<timestamp>/
```

Ensure files are non-empty.

## Restore Procedure

> **Warning:** Restoring will **OVERWRITE** existing data in the containers.
> Ensure you have a backup of the current state if effective data exists.

### Full System Restore

1. Stop the application (optional but recommended to prevent writes).
2. Ensure stateful services are running (`postgres`, `neo4j`, and the active
   object storage backend: `minio` or `seaweed-s3`).
3. Run the restore script:

   ```bash
   ./scripts/restore.sh ./backups/YYYYMMDD_HHMMSS
   ```

4. You will be prompted to confirm. Type `y`.
5. Restart services to ensure volume changes are picked up correctly
   (especially object storage + Milvus).

   ```bash
   docker-compose restart
   ```

### Partial Restore

If you only need to restore specific components, you can manually run the
commands found in `scripts/restore.sh` for the specific service.

## Troubleshooting

- **Neo4j Restore Fails**: Ensure APOC plugin is enabled and `apoc.export.*`
  settings are configured in `docker-compose.yml`.
- **MinIO/Milvus Inconsistency**: If vectors are missing after restore, ensure
  both `minio_data.tar.gz` was restored AND `etcd` volume matches. *Note:
  Current script backs up MinIO data but not Etcd directly. For full Milvus DR,
  it is recommended to stop the stack and backup all volumes, but MinIO restore
  often suffices for data recovery if Etcd is rebuilt (though indexing might
  need regeneration).*
- **SeaweedFS/Milvus Inconsistency**: If Milvus is configured against
  `seaweed-s3`, validate SeaweedFS filer + S3 services are healthy and ensure
  SeaweedFS data volume plus Etcd are restored from the same backup window.
- **Permission Errors**: Ensure the script is run with user permissions that
  can access Docker.
