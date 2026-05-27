"""Smoke tests for app.config.Settings env parsing.

Runs as a plain script (``python tests/test_config.py``) or under pytest.
"""

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]


def _load_settings(cors_value):
    if cors_value is None:
        os.environ.pop("BACKEND_CORS_ORIGINS", None)
    else:
        os.environ["BACKEND_CORS_ORIGINS"] = cors_value
    from app import config

    importlib.reload(config)
    return config.Settings()


def test_json_list_env():
    s = _load_settings('["http://localhost","http://localhost:8080"]')
    assert s.backend_cors_origins == ["http://localhost", "http://localhost:8080"]


def test_comma_separated_env():
    s = _load_settings("http://localhost,http://localhost:8080")
    assert s.backend_cors_origins == ["http://localhost", "http://localhost:8080"]


def test_wildcard_env():
    s = _load_settings("*")
    assert s.backend_cors_origins == ["*"]


def test_single_value_env():
    s = _load_settings("http://localhost")
    assert s.backend_cors_origins == ["http://localhost"]


def test_empty_env_uses_default():
    s = _load_settings("")
    assert s.backend_cors_origins == DEFAULT_ORIGINS


def test_unset_env_uses_default():
    s = _load_settings(None)
    assert s.backend_cors_origins == DEFAULT_ORIGINS


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK  {name}")
    print("All config tests passed.")
