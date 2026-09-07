# Troubleshooting

| Symptom | Check |
|---------|--------|
| API import fails | `pip install -r requirements-dev.txt` |
| `/ready` 503 | Docker Desktop running? `postgres`/`qdrant`/`redis` healthy? |
| Login bcrypt errors | Use `bcrypt` package (not broken passlib+bcrypt combo) |
| Search init `unrecognized token: #` | Fixed in `search/search_index.py` — pull latest |
| Missing weights | `python scripts/download_models.py --check` |
| React blank API errors | Set `frontend/.env` `VITE_API_BASE_URL` / `VITE_WS_URL` |
| Streamlit empty | Ensure `database/identities.db` and run pipeline |
| Docker pipe error on Windows | Start Docker Desktop Linux engine |
