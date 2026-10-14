from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check_python() -> bool:
    return sys.version_info >= (3, 10)

def check_file(path: Path) -> bool:
    return path.exists()

def check_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False

def main() -> int:
    print("=== multicam-reid environment check ===")
    ok = True
    ok &= check_python()
    print(f"Python >= 3.10: {check_python()}")

    core_files = [
        ROOT / "config.yaml",
        ROOT / "yolov8n.pt",
        ROOT / "requirements.txt",
        ROOT / ".env",
        ROOT / "frontend" / "package.json",
    ]
    for p in core_files:
        exists = check_file(p)
        ok &= exists
        print(f"{p.relative_to(ROOT)}: {exists}")

    for module in ["fastapi", "uvicorn", "cv2", "yaml", "ultralytics", "numpy"]:
        exists = check_module(module)
        ok &= exists
        print(f"Python module {module}: {exists}")

    for cmd_name in []:
        pass

    print()
    if ok:
        print("Environment check: PASS")
        return 0
    print("Environment check: FAIL")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())