"""Load a local .env file without adding a runtime dependency.

Existing process variables always win. The parser intentionally supports the
simple KEY=VALUE format used by this project and quoted values.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_env(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise RuntimeError(f"Invalid .env entry on line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
            raise RuntimeError(f"Invalid .env key on line {line_number}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)
