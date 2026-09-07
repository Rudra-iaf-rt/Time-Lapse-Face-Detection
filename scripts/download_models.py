#!/usr/bin/env python3
"""Model weight presence check and documented acquisition paths.

Does not silently download large blobs unless --fetch-torchreid is passed
(and torchreid is installed). Prefer explicit local placement for ArcFace.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"

REQUIRED = {
    "osnet": MODELS / "osnet_x1_0_market_256x128.pth",
    "arcface": MODELS / "arcface_r100_v1.pth",
}


def print_missing_help() -> None:
    print(
        "\nRequired model weights are missing.\n"
        "Run: python scripts/download_models.py --check\n\n"
        "OSNet (Market1501):\n"
        "  - Place file at models/osnet_x1_0_market_256x128.pth\n"
        "  - Or: python scripts/download_models.py --fetch-torchreid\n"
        "    (requires `pip install torchreid` and network access)\n\n"
        "ArcFace:\n"
        "  - Place weights at models/arcface_r100_v1.pth\n"
        "  - InsightFace model zoo packages may be used; copy the .pth/.onnx you standardize on.\n\n"
        "YOLO:\n"
        "  - yolov8n.pt may auto-download via ultralytics on first detect run.\n"
    )


def status() -> int:
    MODELS.mkdir(parents=True, exist_ok=True)
    missing = []
    for name, path in REQUIRED.items():
        ok = path.exists() and path.stat().st_size > 0
        print(f"{name}: {'OK' if ok else 'MISSING'} ({path})")
        if not ok:
            missing.append(name)
    if missing:
        print_missing_help()
        return 1
    print("All configured weight files present.")
    return 0


def fetch_torchreid_osnet() -> int:
    target = REQUIRED["osnet"]
    try:
        import torch
        from torchreid import models
    except Exception as exc:
        print(
            "Required model weights are missing / fetch failed.\n"
            f"torchreid import error: {exc}\n"
            "Install with: pip install torchreid\n"
            "Then re-run: python scripts/download_models.py --fetch-torchreid"
        )
        return 1

    try:
        model = models.build_model(name="osnet_x1_0", num_classes=751, pretrained=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), target)
        print(f"Wrote OSNet weights to {target} ({target.stat().st_size} bytes)")
        return 0
    except Exception as exc:
        print(
            "Required model weights are missing.\n"
            f"Fetch failed: {exc}\n"
            "Place OSNet weights manually at models/osnet_x1_0_market_256x128.pth"
        )
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or fetch model weights")
    parser.add_argument("--check", action="store_true", help="Check presence only")
    parser.add_argument(
        "--fetch-torchreid",
        action="store_true",
        help="Attempt OSNet download via torchreid (optional network)",
    )
    args = parser.parse_args()
    if args.fetch_torchreid:
        code = fetch_torchreid_osnet()
        if code != 0:
            return code
    return status()


if __name__ == "__main__":
    sys.exit(main())
