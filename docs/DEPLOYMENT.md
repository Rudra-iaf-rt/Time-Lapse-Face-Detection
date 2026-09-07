# Deployment

```bash
docker compose -f docker/docker-compose.yml up -d postgres qdrant redis
docker compose -f docker/docker-compose.yml --profile full up -d --build
docker compose -f docker/docker-compose.yml --profile tools up -d   # pgadmin, redis-commander
```

CI workflows:

- `.github/workflows/test.yml` — pytest + frontend build
- `.github/workflows/build.yml` — image/frontend build
- `.github/workflows/deploy.yml` — **manual only**, no cloud provider credentials assumed

Backup/restore: `deployment/recovery/`.
