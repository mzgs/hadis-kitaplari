#!/usr/bin/env python3
"""Report missing fields in Turkish hadith book JSON files.

Missing means the key is absent, the value is null, or the value is an empty
string after trimming whitespace.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOK_DIR = ROOT / "turkish_books"


def is_missing(record: dict[str, Any], key: str) -> bool:
    if key not in record:
        return True

    value = record[key]
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict, tuple, set)):
        return not value

    return False


def iter_records(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(data, dict):
        for chapter_records in data.values():
            if not isinstance(chapter_records, list):
                continue

            for item in chapter_records:
                if isinstance(item, dict):
                    yield item


def scan_file(path: Path) -> dict[str, int | str]:
    data = json.loads(path.read_text(encoding="utf-8"))

    records = 0
    turkish_missing = 0
    arabic_missing = 0
    chain_missing = 0

    for record in iter_records(data):
        records += 1

        missing_turkish = is_missing(record, "turkce")
        missing_arabic = is_missing(record, "arabic")
        missing_chain = is_missing(record, "chain")

        turkish_missing += int(missing_turkish)
        arabic_missing += int(missing_arabic)
        chain_missing += int(missing_chain)

    return {
        "file": path.name,
        "records": records,
        "turkish_missing": turkish_missing,
        "arabic_missing": arabic_missing,
        "chain_missing": chain_missing,
    }


def format_number(value: int | str) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    return value


def print_table(rows: list[dict[str, int | str]]) -> None:
    headers = [
        "File",
        "Records",
        "Turkish missing",
        "Arabic missing",
        "Chain missing",
    ]
    keys = [
        "file",
        "records",
        "turkish_missing",
        "arabic_missing",
        "chain_missing",
    ]

    table_rows = [[format_number(row[key]) for key in keys] for row in rows]
    widths = [
        max(len(header), *(len(row[index]) for row in table_rows))
        for index, header in enumerate(headers)
    ]

    print("| " + " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)) + " |")
    print("| " + " | ".join("-" * width for width in widths) + " |")
    for row in table_rows:
        print("| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Turkish hadith books and report missing fields.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Specific JSON files to scan. Defaults to all files in turkish_books/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = args.files or sorted(DEFAULT_BOOK_DIR.glob("*.json"))

    rows = [scan_file(path if path.is_absolute() else ROOT / path) for path in paths]
    print_table(rows)


if __name__ == "__main__":
    main()
