from __future__ import annotations

import argparse
import secrets
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
BACKUP = ROOT / ".env.pre-rotation.bak"


def make_secret(n: int = 48) -> str:
    return secrets.token_urlsafe(n)


def update_env(apply: bool) -> str:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    values = {
        "JWT_SECRET": make_secret(48),
        "ADMIN_PASSWORD": make_secret(18),
        "OPERATOR_PASSWORD": make_secret(18),
        "VIEWER_PASSWORD": make_secret(18),
        "POSTGRES_PASSWORD": make_secret(18),
    }
    out = []
    seen = set()
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in values:
                out.append(f"{key}={values[key]}")
                seen.add(key)
                continue
        out.append(line)
    for key, value in values.items():
        if key not in seen:
            out.append(f"{key}={value}")

    text = "\n".join(out) + "\n"
    if apply:
        if ENV.exists():
            shutil.copy2(ENV, BACKUP)
        ENV.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate development secrets in .env")
    parser.add_argument("--apply", action="store_true", help="Write new secrets to .env")
    args = parser.parse_args()

    result = update_env(args.apply)
    if args.apply:
        print("Secrets rotated. Backup written to .env.pre-rotation.bak")
        print("Restart the API and update running services with the new values.")
    else:
        print("Dry run. Use --apply to write changes.")
        print(result)


if __name__ == "__main__":
    main()