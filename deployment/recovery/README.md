# Backup & Recovery

## PostgreSQL

```bash
# Backup
CONFIRM=yes ./deployment/recovery/backup_postgres.sh

# Restore (DESTRUCTIVE)
CONFIRM=yes ./deployment/recovery/restore_postgres.sh ./backups/postgres_XXXX.sql
```

Windows PowerShell equivalents: `backup_postgres.ps1` / `restore_postgres.ps1`.

Scripts **refuse to run** destructive restore without `CONFIRM=yes`.

## Qdrant

Qdrant stores vectors under its storage volume (`qdrant_data`). Snapshot via Qdrant API or volume backup:

- Stop writers
- Copy `/qdrant/storage` volume
- Or use Qdrant snapshot endpoints for the collections `face_embeddings` / `reid_embeddings`

## Configuration recovery

- Restore `.env` from secret store (never from git)
- Restore `config.yaml` from version control
- Re-run `docker compose up -d postgres qdrant redis`

## Failure recovery

1. Check `/live` then `/ready`
2. Inspect `docker compose logs`
3. Restore Postgres if relational data lost
4. Rehydrate Qdrant from snapshots if vector search broken
5. SQLite `database/identities.db` remains the Streamlit fallback and is independent
