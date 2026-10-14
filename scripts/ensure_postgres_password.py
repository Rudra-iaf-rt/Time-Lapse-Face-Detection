from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def load_env() -> None:
    if not ENV.exists():
        return
    for raw in ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_env()
    password = os.environ.get("POSTGRES_PASSWORD", "change-me")
    user = os.environ.get("POSTGRES_USER", "postgres")
    container = "multicam_postgres"
    sql = f"ALTER USER {user} PASSWORD '{password}';"
    result = subprocess.run(
        ["docker", "exec", container, "psql", "-U", user, "-c", sql],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(result.returncode)
    print(f"PostgreSQL password synchronized for user '{user}'.")


if __name__ == "__main__":
    main()