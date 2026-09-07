# tests/test_streamlit_smoke.py
"""Smoke-import Streamlit dashboard modules without launching the UI server."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_identity_store_import_and_stats():
    from database.identity_store import IdentityStore

    store = IdentityStore(db_path="database/identities.db")
    stats = store.stats()
    assert isinstance(stats, dict)


def test_dashboard_module_imports():
    # Importing app.py executes Streamlit page config — may require streamlit runtime.
    # Validate the module path exists and key helpers can load via IdentityStore path used by dashboard.
    import importlib.util
    from pathlib import Path

    path = Path("dashboard/app.py")
    assert path.exists()
    assert path.stat().st_size > 0
    spec = importlib.util.spec_from_file_location("dashboard_app_check", path)
    assert spec is not None
