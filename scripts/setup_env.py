#!/usr/bin/env python3
"""Create a syntactically valid local .env from the visible delivery template."""
from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_CANDIDATES = (ROOT / ".env.example",)
TARGET = ROOT / ".env"
KEY_VALUE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def validate_env(path: Path) -> None:
    invalid: list[tuple[int, str]] = []
    duplicate_keys: list[str] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not KEY_VALUE.fullmatch(line):
            invalid.append((line_number, line))
            continue
        key = line.split("=", 1)[0]
        if key in seen:
            duplicate_keys.append(key)
        seen.add(key)
    if invalid:
        details = ", ".join(f"line {number}: {value!r}" for number, value in invalid)
        raise SystemExit(f"Invalid .env syntax in {path.name}: {details}")
    if duplicate_keys:
        raise SystemExit(
            f"Duplicate .env keys in {path.name}: {', '.join(sorted(set(duplicate_keys)))}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing .env after first creating a timestamped backup.",
    )
    args = parser.parse_args()

    source = next((path for path in SOURCE_CANDIDATES if path.is_file()), None)
    if source is None:
        raise SystemExit(".env.example does not exist.")
    validate_env(source)

    if TARGET.exists():
        validate_env(TARGET)
        if not args.force:
            print(".env already exists and is valid. Use --force to rebuild it.")
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = ROOT / f".env.backup-{stamp}"
        shutil.copy2(TARGET, backup)
        print(f"Existing .env backed up as {backup.name}")

    shutil.copy2(source, TARGET)
    validate_env(TARGET)
    print(f"Created valid local .env from {source.name}.")
    print("Local demo secrets are not suitable for production deployment.")


if __name__ == "__main__":
    main()
