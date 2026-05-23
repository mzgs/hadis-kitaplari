#!/usr/bin/env python3
"""Parse HadithUnlocked pages into structured JSON.

Examples:
  python parse_hadithunlocked.py --url https://hadithunlocked.com/bukhari/65/2 -o bukhari_65_2.json
  python parse_hadithunlocked.py --collection bukhari -o bukhari_hu.json --delay 1
  python parse_hadithunlocked.py --all-collections -o hadithunlocked_collections --delay 1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://hadithunlocked.com/"
BOOKS_URL = "https://hadithunlocked.com/books"
USER_AGENT = "hadithunlocked-json-parser/1.0 (+https://hadithunlocked.com/)"


@dataclass(frozen=True)
class CollectionLink:
    slug: str
    name: str
    url: str


@dataclass(frozen=True)
class ChapterLink:
    number: int | None
    url: str
    english_name: str | None = None
    arabic_name: str | None = None


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*", "\n", value)
    value = value.strip(" \n:")
    return value or None


def text_from(node: Tag | None, separator: str = " ") -> str | None:
    if node is None:
        return None
    return clean_text(node.get_text(separator=separator, strip=True))


def markdown_source_or_text(node: Tag | None, separator: str = " ") -> str | None:
    if node is None:
        return None
    return clean_text(node.get("data-markdown-source")) or text_from(node, separator)


def combine_parts(parts: list[str | None], separator: str) -> str | None:
    values = [part for part in parts if part]
    return clean_text(separator.join(values)) if values else None


def fetch(session: requests.Session, url: str, timeout: int) -> tuple[BeautifulSoup, str]:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser"), response.url


def normalize_url(url_or_path: str) -> str:
    return urljoin(BASE_URL, url_or_path)


def safe_hadithunlocked_url(page_url: str, href: str | None) -> str | None:
    href = clean_text(href)
    if not href or href.lower() in {"null", "/null", "undefined", "none", "#"}:
        return None

    url = urljoin(page_url, href)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc not in {"hadithunlocked.com", "www.hadithunlocked.com"}:
        return None
    if parsed.path in {"", "/", "/null"}:
        return None
    return url


def slug_from_url(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[0]


def page_path_parts(url: str) -> list[str]:
    return [part for part in urlparse(url).path.split("/") if part]


def collection_name(soup: BeautifulSoup, slug: str | None) -> str | None:
    node = soup.select_one('[data-prop="book.name_en"]')
    if node:
        return text_from(node)

    for script in soup.select('script[type="application/ld+json"]'):
        text = script.string
        if not text or '"@type": "Book"' not in text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if data.get("@type") == "Book" and data.get("inLanguage") == "English":
            return clean_text(data.get("name"))

    title = text_from(soup.find("title"))
    if title:
        title = re.sub(r"^Ḥadīth Unlocked \| Contents of ", "", title)
        title = re.sub(r"^Ḥadīth \| ", "", title)
        return clean_text(title.split("(", 1)[0])
    return slug


def heading_for_url(soup: BeautifulSoup, page_url: str) -> tuple[str | None, str | None]:
    path = urlparse(page_url).path
    english = soup.select_one(f'[data-prop="toc.title_en"][href="{path}"]')
    arabic = soup.select_one(f'[data-prop="toc.title"][href="{path}"]')
    if english or arabic:
        return text_from(english), text_from(arabic)
    return None, None


def parse_collection_links(soup: BeautifulSoup) -> list[CollectionLink]:
    collections: list[CollectionLink] = []
    seen: set[str] = set()
    for anchor in soup.select('main a.btn[href^="/"]'):
        href = anchor.get("href")
        if not href:
            continue
        parts = [part for part in href.split("/") if part]
        if len(parts) != 1 or parts[0] == "quran":
            continue
        slug = parts[0]
        if slug in seen:
            continue
        seen.add(slug)
        collections.append(
            CollectionLink(
                slug=slug,
                name=text_from(anchor) or slug,
                url=normalize_url(href),
            )
        )
    return collections


def parse_chapter_links(soup: BeautifulSoup, page_url: str) -> list[ChapterLink]:
    chapters: list[ChapterLink] = []
    seen: set[str] = set()
    for row in soup.select("#toc tr.chapter"):
        english = row.select_one('[data-prop="toc.title_en"][href]')
        arabic = row.select_one('[data-prop="toc.title"][href]')
        anchor = english or arabic
        if not anchor:
            continue
        url = safe_hadithunlocked_url(page_url, anchor.get("href"))
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        number = text_from(row.find("td"))
        chapters.append(
            ChapterLink(
                number=int(number) if number and number.isdigit() else None,
                url=url,
                english_name=text_from(english),
                arabic_name=text_from(arabic),
            )
        )
    return chapters


def reference_from_article(article: Tag) -> str | None:
    reference = article.select_one('section[lang="en"] b a[href*=":"]')
    if not reference:
        reference = article.select_one('a[href*=":"]')
    return text_from(reference)


def parse_hadith_articles(
    soup: BeautifulSoup,
    skip_english_translation: bool = False,
) -> list[dict[str, Any]]:
    hadiths: list[dict[str, Any]] = []
    for article in soup.select("article.row"):
        if not article.select_one('[data-prop="hadith.body"], [data-prop="hadith.body_en"]'):
            continue

        chain = text_from(article.select_one('[data-prop="hadith.chain_en"]')) or text_from(
            article.select_one('[data-prop="hadith.chain"]')
        )
        english = None
        if not skip_english_translation:
            english = markdown_source_or_text(
                article.select_one('[data-prop="hadith.body_en"]'),
                separator="\n",
            )
        arabic = markdown_source_or_text(article.select_one('[data-prop="hadith.body"]'))
        body_node = article.select_one('[data-prop="hadith.body"], [data-prop="hadith.body_en"]')
        hadith_id = clean_text(body_node.get("data-id")) if body_node else None

        hadith = {
            "reference": reference_from_article(article),
            "hadith_unlocked_id": int(hadith_id) if hadith_id and hadith_id.isdigit() else hadith_id,
            "chain": chain,
            "arabic": arabic,
            "grade": text_from(article.select_one("aside.grade")),
        }
        if not skip_english_translation:
            hadith["english"] = english
        hadiths.append(hadith)
    return hadiths


def next_page_url(soup: BeautifulSoup, page_url: str) -> str | None:
    anchor = soup.select_one('a[rel="next"][href]')
    if not anchor:
        return None
    return safe_hadithunlocked_url(page_url, anchor.get("href"))


def same_chapter_prefix(start_url: str, candidate_url: str) -> bool:
    start = page_path_parts(start_url)
    candidate = page_path_parts(candidate_url)
    if len(start) < 2 or len(candidate) < 2:
        return False
    return candidate[:2] == start[:2]


def parse_chapter_page(
    session: requests.Session,
    chapter_link: ChapterLink,
    args: argparse.Namespace,
) -> dict[str, Any]:
    hadiths: list[dict[str, Any]] = []
    seen_pages: set[str] = set()
    seen_references: set[str] = set()
    page_url = chapter_link.url

    while page_url not in seen_pages:
        seen_pages.add(page_url)
        soup, final_url = fetch(session, page_url, args.timeout)
        print(f"Parsing {final_url}", file=sys.stderr)

        for hadith in parse_hadith_articles(soup, args.skip_english_translation):
            dedupe_key = hadith.get("reference") or str(hadith.get("hadith_unlocked_id"))
            if dedupe_key and dedupe_key in seen_references:
                continue
            if dedupe_key:
                seen_references.add(dedupe_key)
            hadiths.append(hadith)

        next_url = next_page_url(soup, final_url)
        if not next_url or not same_chapter_prefix(chapter_link.url, next_url):
            break
        if args.max_pages and len(seen_pages) >= args.max_pages:
            break
        if args.delay > 0:
            time.sleep(args.delay)
        page_url = next_url

    return {
        "book_number": chapter_link.number,
        "book_name": chapter_link.english_name,
        "arabic_book_name": chapter_link.arabic_name,
        "content": hadiths,
    }


def parse_collection_page(
    session: requests.Session,
    start_url: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    soup, final_url = fetch(session, start_url, args.timeout)
    slug = slug_from_url(final_url)
    chapters = parse_chapter_links(soup, final_url)

    if not chapters and parse_hadith_articles(soup, args.skip_english_translation):
        english_name, arabic_name = heading_for_url(soup, final_url)
        chapter = ChapterLink(
            number=None,
            url=final_url,
            english_name=english_name or collection_name(soup, slug),
            arabic_name=arabic_name,
        )
        return {
            "collection": collection_name(soup, slug),
            "books": [parse_chapter_page(session, chapter, args)],
        }

    if not chapters:
        raise RuntimeError(f"No chapter links or hadiths found at {start_url}")

    if args.max_books:
        chapters = chapters[: args.max_books]

    books = []
    for index, chapter in enumerate(chapters, start=1):
        if index > 1 and args.delay > 0:
            time.sleep(args.delay)
        books.append(parse_chapter_page(session, chapter, args))

    return {
        "collection": collection_name(soup, slug),
        "books": books,
    }


def parse_all_collections(args: argparse.Namespace) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})
    books_page, _ = fetch(session, BOOKS_URL, args.timeout)
    collection_links = parse_collection_links(books_page)

    if args.max_collections:
        collection_links = collection_links[: args.max_collections]
    if not collection_links:
        raise RuntimeError("No collections found on HadithUnlocked")

    os.makedirs(args.output, exist_ok=True)
    written_files = []
    skipped_files = []
    for index, collection in enumerate(collection_links, start=1):
        output_path = os.path.join(args.output, f"{collection.slug}.json")
        if os.path.exists(output_path):
            print(f"Skipping existing file {output_path}", file=sys.stderr)
            skipped_files.append(output_path)
            continue

        if index > 1 and args.delay > 0:
            time.sleep(args.delay)
        print(f"Parsing collection {collection.url}", file=sys.stderr)
        try:
            data = parse_collection_page(session, collection.url, args)
            write_json(output_path, data, args.indent)
            written_files.append(output_path)
        except Exception as exc:
            print(f"Failed {collection.url}: {exc}", file=sys.stderr)
            if not args.skip_errors:
                raise

    return {
        "output_directory": args.output,
        "files": written_files,
        "skipped_files": skipped_files,
    }


def parse_url(args: argparse.Namespace) -> dict[str, Any]:
    if args.all_collections:
        return parse_all_collections(args)

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})
    start_url = normalize_url(args.url or args.collection)
    if args.collection and not args.url:
        start_url = normalize_url(args.collection.strip("/") + "/")

    return parse_collection_page(session, start_url, args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse HadithUnlocked pages into structured JSON."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="HadithUnlocked collection, chapter, or page URL.")
    source.add_argument("--collection", help="Collection slug such as bukhari or hakim.")
    source.add_argument(
        "--all-collections",
        action="store_true",
        help="Parse every collection found on HadithUnlocked's books page.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output JSON file path. With --all-collections, this is an output directory.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between page requests. Default: 1.0",
    )
    parser.add_argument(
        "--max-books",
        type=int,
        help="Limit collection parsing to the first N chapter entries.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Limit pages followed inside each chapter entry.",
    )
    parser.add_argument(
        "--max-collections",
        type=int,
        help="Limit --all-collections parsing to the first N collections.",
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continue when a collection fails during --all-collections parsing.",
    )
    parser.add_argument(
        "--skip-english-translation",
        action="store_true",
        help="Do not include HadithUnlocked's English hadith body translation.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout seconds.")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation.")
    parser.add_argument("--user-agent", default=USER_AGENT, help="HTTP User-Agent.")
    return parser


def write_json(path: str, data: dict[str, Any], indent: int) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=indent)
        handle.write("\n")


def main() -> int:
    args = build_parser().parse_args()
    data = parse_url(args)
    if not args.all_collections:
        write_json(args.output, data, args.indent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
