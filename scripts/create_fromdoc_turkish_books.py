#!/usr/bin/env python3
"""Create fixed-schema Turkish hadith JSON files from fawazahmed0/hadith-api."""

from __future__ import annotations

import json
import urllib.request
from collections import OrderedDict
from pathlib import Path


BASE_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions"
OUT_DIR = Path("fromdoc")
LOCAL_FALLBACKS = {
    "abudawud": Path("turkish_books/ebudavud.json"),
    "bukhari": Path("turkish_books/buhari.json"),
    "ibnmajah": Path("turkish_books/ibnmace.json"),
    "malik": Path("turkish_books/malik.json"),
    "muslim": Path("turkish_books/muslim.json"),
    "nasai": Path("turkish_books/nasai.json"),
    "nawawi": Path("turkish_books/nevevi40.json"),
    "tirmidhi": Path("turkish_books/tirmizi.json"),
}


def load_edition(slug: str) -> dict:
    url = f"{BASE_URL}/{slug}.json"
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def hadith_key(hadith: dict) -> tuple[object, object, object]:
    reference = hadith.get("reference") or {}
    return (
        hadith.get("hadithnumber"),
        reference.get("book"),
        reference.get("hadith"),
    )


def load_local_fallback(book_slug: str) -> dict[object, dict]:
    path = LOCAL_FALLBACKS.get(book_slug)
    if path is None or not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    fallback = {}
    for hadiths in data.values():
        for hadith in hadiths:
            fallback[hadith.get("hadith_no")] = hadith
    return fallback


def discover_turkish_editions() -> list[dict]:
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions.json"
    ) as response:
        editions = json.load(response)

    turkish = []
    for collection in editions.values():
        for edition in collection.get("collection", []):
            if edition.get("language") == "Turkish":
                turkish.append(edition)
    return turkish


def build_fixed_schema(turkish_slug: str, arabic_slug: str) -> tuple[dict, int]:
    book_slug = turkish_slug.removeprefix("tur-")
    turkish = load_edition(turkish_slug)
    arabic = load_edition(arabic_slug)

    collection_name = text(turkish["metadata"]["name"])
    sections = turkish["metadata"].get("sections", {})
    arabic_by_key = {hadith_key(hadith): hadith for hadith in arabic["hadiths"]}
    local_fallback = load_local_fallback(book_slug)

    books: OrderedDict[int, dict] = OrderedDict()
    missing_arabic = []
    skipped = 0

    for turkish_hadith in turkish["hadiths"]:
        key = hadith_key(turkish_hadith)
        arabic_hadith = arabic_by_key.get(key)
        if arabic_hadith is None:
            missing_arabic.append(key)
            arabic_text = ""
        else:
            arabic_text = text(arabic_hadith.get("text"))
        turkish_text = text(turkish_hadith.get("text"))

        if not arabic_text or not turkish_text:
            local_hadith = local_fallback.get(turkish_hadith.get("hadithnumber"), {})
            arabic_text = arabic_text or text(local_hadith.get("arabic"))
            turkish_text = turkish_text or text(local_hadith.get("turkish"))
        if not arabic_text or not turkish_text:
            skipped += 1
            continue

        reference = turkish_hadith.get("reference") or {}
        book_no = int(reference.get("book") or 0)
        book = books.setdefault(
            book_no,
            {
                "book_name": text(sections.get(str(book_no))) or f"Book {book_no}",
                "content": [],
            },
        )
        book["content"].append(
            {
                "reference": f"{collection_name} {turkish_hadith.get('hadithnumber')}",
                "arabic": arabic_text,
                "turkish": turkish_text,
            }
        )

    if missing_arabic:
        raise RuntimeError(f"{turkish_slug}: missing Arabic matches: {missing_arabic[:5]}")

    return (
        {
            "collection": collection_name,
            "books": [book for _, book in books.items()],
        },
        skipped,
    )


def validate(data: dict, output: Path) -> tuple[int, int]:
    books = data.get("books", [])
    hadiths = [hadith for book in books for hadith in book.get("content", [])]
    bad = [
        hadith
        for hadith in hadiths
        if set(hadith) != {"reference", "arabic", "turkish"}
        or not hadith.get("reference")
        or not hadith.get("arabic")
        or not hadith.get("turkish")
    ]
    if bad:
        raise RuntimeError(f"{output}: invalid hadith entries: {len(bad)}")
    return len(books), len(hadiths)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    results = []

    for edition in discover_turkish_editions():
        book_slug = edition["book"]
        turkish_slug = edition["name"]
        arabic_slug = f"ara-{book_slug}"
        output = OUT_DIR / f"{turkish_slug}.json"

        data, skipped = build_fixed_schema(turkish_slug, arabic_slug)
        book_count, hadith_count = validate(data, output)
        output.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        results.append((output, book_count, hadith_count, skipped))

    for output, book_count, hadith_count, skipped in results:
        print(
            f"{output}: {book_count} books, {hadith_count} hadiths"
            f" ({skipped} skipped empty source rows)"
        )


if __name__ == "__main__":
    main()
