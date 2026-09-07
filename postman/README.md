# Postman / Newman

## Import

1. Import `multicam-reid.postman_collection.json`
2. Import `multicam-reid.postman_environment.json`
3. Set `username` / `password` from your `.env` (do not commit real secrets)

## Newman

```bash
npx newman run postman/multicam-reid.postman_collection.json \
  -e postman/multicam-reid.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export postman/newman-report.json
```

Requires the API listening on `baseUrl`.

WebSocket checks are documented via `wsUrl` but Newman HTTP collection focuses on REST.
