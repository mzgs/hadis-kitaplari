#!/usr/bin/env python3
"""Parse Sunnah.com collection/book pages into structured JSON.

Examples:
  python parse_sunnah.py --url https://sunnah.com/bukhari/1 -o bukhari_book_1.json
  python parse_sunnah.py --url https://sunnah.com/bukhari -o bukhari.json --delay 1
  python parse_sunnah.py --url https://sunnah.com/bukhari/1 -o bukhari_book_1.json --skip-english-translation
  python parse_sunnah.py --collection muslim -o muslim.json --max-books 2
  python parse_sunnah.py --all-collections -o collections --delay 1
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


BASE_URL = "https://sunnah.com/"
HADITH_UNLOCKED_BASE_URL = "https://hadithunlocked.com/"
USER_AGENT = "sunnah-json-parser/1.0 (+https://sunnah.com/)"
COLLECTION_SELECTOR_URL = "https://sunnah.com/bukhari/1"
DEFAULT_COLLECTIONS = [
    ("bukhari", "Sahih el-Buhari"),
    ("muslim", "Sahih-i Müslim"),
    ("nasai", "Sünen en-Nesâî"),
    ("abudawud", "Sünen Ebû Dâvûd"),
    ("tirmidhi", "Câmiu’t-Tirmizî"),
    ("ibnmajah", "Sünen İbn Mâce"),
    ("malik", "Muvatta İmam Mâlik"),
    ("ahmad", "Müsned Ahmed bin Hanbel"),
    ("darimi", "Sünen ed-Dârimî"),
    ("ibnkhuzayma", "Sahih İbn Huzeyme"),
    ("ibnhibban", "Sahih İbn Hibban"),
    ("hakim", "Müstedrek el-Hâkim"),
    ("nawawi40", "İmam Nevevî’nin 40 Hadisi"),
    ("riyadussalihin", "Riyâzü’s-Sâlihîn"),
    ("adab", "el-Edebü’l-Müfred"),
    ("shamail", "eş-Şemâilü’l-Muhammediyye"),
    ("mishkat", "Mişkâtü’l-Mesâbîh"),
    ("bulugh", "Bülûğu’l-Merâm"),
    ("forty", "Kırk Hadis Koleksiyonları"),
    ("hisn", "Hısnü’l-Müslim"),
    ("virtues", "Kur’an Sure ve Ayetlerinin Faziletleri"),
]


@dataclass(frozen=True)
class BookLink:
    number: int | None
    url: str
    english_name: str | None = None
    arabic_name: str | None = None


@dataclass(frozen=True)
class CollectionLink:
    slug: str
    name: str
    url: str


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


def fetch(session: requests.Session, url: str, timeout: int) -> BeautifulSoup:
    soup, _ = fetch_with_final_url(session, url, timeout)
    return soup


def fallback_url_for(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc not in {"sunnah.com", "www.sunnah.com"}:
        return None
    if parsed.path.strip("/") != "hakim/29":
        return None
    fallback_url = urljoin(HADITH_UNLOCKED_BASE_URL, parsed.path.lstrip("/"))
    return f"{fallback_url}?{parsed.query}" if parsed.query else fallback_url


def fetch_with_final_url(
    session: requests.Session,
    url: str,
    timeout: int,
) -> tuple[BeautifulSoup, str]:
    response = session.get(url, timeout=timeout)
    if response.status_code >= 500:
        fallback_url = fallback_url_for(url)
        if fallback_url:
            print(
                f"{url} returned HTTP {response.status_code}; using {fallback_url}",
                file=sys.stderr,
            )
            response = session.get(fallback_url, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser"), response.url


def normalize_url(url_or_path: str) -> str:
    return urljoin(BASE_URL, url_or_path)


def safe_hadith_unlocked_url(page_url: str, href: str | None) -> str | None:
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


def collection_slug_from_url(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[0]


def parse_collection_name(soup: BeautifulSoup, slug: str | None) -> str | None:
    breadcrumb = soup.select("div.crumbs a")
    if breadcrumb:
        candidate = text_from(breadcrumb[-1])
        if candidate and candidate.lower() != "home":
            return candidate
    breadcrumb = soup.select("section.breadcrumbs a")
    if breadcrumb:
        candidate = text_from(breadcrumb[0])
        if candidate and candidate.lower() != "home":
            return candidate
    title = text_from(soup.find("title"))
    if title:
        return title.split(" - Sunnah.com", 1)[0]
    return slug


def parse_book_links(soup: BeautifulSoup, page_url: str) -> list[BookLink]:
    books: list[BookLink] = []
    for book_node in soup.select(".book_title"):
        anchor = book_node.find("a", href=True)
        if not anchor:
            continue
        number = text_from(book_node.select_one(".book_number"))
        books.append(
            BookLink(
                number=int(number) if number and number.isdigit() else None,
                url=urljoin(page_url, anchor["href"]),
                english_name=text_from(book_node.select_one(".english_book_name")),
                arabic_name=text_from(book_node.select_one(".arabic_book_name")),
            )
        )
    return books


def parse_collection_links(soup: BeautifulSoup) -> list[CollectionLink]:
    collections: list[CollectionLink] = []
    seen: set[str] = set()
    for chip in soup.select("#collectionChips .chip[data-value]"):
        slug = clean_text(chip.get("data-value"))
        name = text_from(chip)
        if not slug or not name or slug in seen:
            continue
        seen.add(slug)
        collections.append(
            CollectionLink(
                slug=slug,
                name=name,
                url=normalize_url(slug + "/"),
            )
        )
    return collections


def default_collection_links() -> list[CollectionLink]:
    return [
        CollectionLink(slug=slug, name=name, url=normalize_url(slug + "/"))
        for slug, name in DEFAULT_COLLECTIONS
    ]


def parse_reference_table(container: Tag) -> dict[str, str]:
    references: dict[str, str] = {}
    table = container.select_one("table.hadith_reference")
    if not table:
        return references

    for row in table.select("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        key = text_from(cells[0])
        value = text_from(cells[1])
        if key and value:
            references[key] = value
    return references


def parse_book_page(
    session: requests.Session,
    book_link: BookLink,
    timeout: int,
    skip_english_translation: bool = False,
) -> dict[str, Any]:
    soup, page_url = fetch_with_final_url(session, book_link.url, timeout)

    if is_hadith_unlocked_page(soup, page_url):
        return parse_hadith_unlocked_book_page(
            session,
            soup,
            page_url,
            book_link,
            timeout,
            skip_english_translation,
        )

    english_name = text_from(soup.select_one(".book_page_english_name")) or book_link.english_name

    hadiths = []
    for container in soup.select(".actualHadithContainer"):
        references = parse_reference_table(container)
        primary_reference = (
            text_from(container.select_one(".hadith_reference_sticky"))
            or references.get("Reference")
        )

        arabic_node = container.select_one(".arabic_hadith_full")

        hadith = {
            "reference": primary_reference,
        }
        if not skip_english_translation:
            english_node = container.select_one(".english_hadith_full")
            hadith["english"] = text_from(english_node, separator="\n")
        hadith["arabic"] = text_from(arabic_node, separator=" ")
        hadiths.append(hadith)

    return {
        "book_name": english_name,
        "content": hadiths,
    }


def markdown_source_or_text(node: Tag | None, separator: str = " ") -> str | None:
    if node is None:
        return None
    markdown_source = clean_text(node.get("data-markdown-source"))
    return markdown_source or text_from(node, separator=separator)


def combine_parts(parts: list[str | None], separator: str) -> str | None:
    values = [part for part in parts if part]
    return clean_text(separator.join(values)) if values else None


def is_hadith_unlocked_page(soup: BeautifulSoup, page_url: str) -> bool:
    parsed = urlparse(page_url)
    if parsed.netloc not in {"hadithunlocked.com", "www.hadithunlocked.com"}:
        return False
    return bool(soup.select_one('article.row [data-prop="hadith.body"]'))


def hadith_unlocked_book_name(soup: BeautifulSoup, book_link: BookLink) -> str | None:
    return (
        text_from(soup.select_one('heading.major h2[lang="en"] [data-prop="toc.title_en"]'))
        or text_from(soup.select_one('heading.major h2[lang="en"]'))
        or book_link.english_name
    )


def parse_hadith_unlocked_book_page(
    session: requests.Session,
    first_soup: BeautifulSoup,
    first_url: str,
    book_link: BookLink,
    timeout: int,
    skip_english_translation: bool = False,
) -> dict[str, Any]:
    book_name = hadith_unlocked_book_name(first_soup, book_link)
    hadiths: list[dict[str, str | None]] = []
    seen_references: set[str] = set()
    seen_pages: set[str] = set()
    book_path = urlparse(first_url).path

    soup = first_soup
    page_url = first_url
    while page_url not in seen_pages:
        seen_pages.add(page_url)

        for article in soup.select("main.chapter article.row, article.row"):
            reference_node = article.select_one('section[lang="en"] b a[href*=":"]')
            if not reference_node:
                continue

            primary_reference = text_from(reference_node)
            if primary_reference and primary_reference in seen_references:
                continue
            if primary_reference:
                seen_references.add(primary_reference)

            arabic = combine_parts(
                [
                    text_from(article.select_one('[data-prop="hadith.chain"]')),
                    markdown_source_or_text(article.select_one('[data-prop="hadith.body"]')),
                ],
                " ",
            )

            hadith = {
                "reference": primary_reference,
            }
            if not skip_english_translation:
                hadith["english"] = combine_parts(
                    [
                        text_from(article.select_one('[data-prop="hadith.chain_en"]')),
                        markdown_source_or_text(
                            article.select_one('[data-prop="hadith.body_en"]'),
                            separator="\n",
                        ),
                    ],
                    "\n",
                )
            hadith["arabic"] = arabic
            hadiths.append(hadith)

        next_link = soup.select_one('a[rel="next"][href]')
        if not next_link:
            break
        next_url = safe_hadith_unlocked_url(page_url, next_link.get("href"))
        if not next_url:
            break
        if urlparse(next_url).path != book_path:
            break
        if next_url in seen_pages:
            break
        soup, page_url = fetch_with_final_url(session, next_url, timeout)

    return {
        "book_name": book_name,
        "content": hadiths,
    }


def is_book_page(soup: BeautifulSoup) -> bool:
    return bool(
        soup.select_one(".actualHadithContainer")
        or soup.select_one('article.row [data-prop="hadith.body"]')
    )


def parse_collection_page(
    session: requests.Session,
    start_url: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    soup = fetch(session, start_url, args.timeout)
    slug = collection_slug_from_url(start_url)

    if is_book_page(soup):
        book = parse_book_page(
            session,
            BookLink(number=None, url=start_url),
            args.timeout,
            args.skip_english_translation,
        )
        collection_name = parse_collection_name(soup, slug)
        return {
            "collection": collection_name,
            "books": [book],
        }

    book_links = parse_book_links(soup, start_url)
    if not book_links:
        raise RuntimeError(f"No book links or hadiths found at {start_url}")

    if args.max_books:
        book_links = book_links[: args.max_books]

    books = []
    for index, book_link in enumerate(book_links, start=1):
        if index > 1 and args.delay > 0:
            time.sleep(args.delay)
        print(f"Parsing {book_link.url}", file=sys.stderr)
        books.append(
            parse_book_page(
                session,
                book_link,
                args.timeout,
                args.skip_english_translation,
            )
        )

    return {
        "collection": parse_collection_name(soup, slug),
        "books": books,
    }


def parse_all_collections(args: argparse.Namespace) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})
    selector_page = fetch(session, COLLECTION_SELECTOR_URL, args.timeout)
    selector_links = {
        collection.slug: collection for collection in parse_collection_links(selector_page)
    }
    collection_links = [
        selector_links.get(collection.slug, collection)
        for collection in default_collection_links()
    ]

    if args.max_collections:
        collection_links = collection_links[: args.max_collections]

    if not collection_links:
        raise RuntimeError("No collections found on Sunnah.com")

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
        description="Parse Sunnah.com pages into structured JSON."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Sunnah.com collection or book URL.")
    source.add_argument(
        "--collection",
        help="Collection slug such as bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah.",
    )
    source.add_argument(
        "--all-collections",
        action="store_true",
        help="Parse every collection found in Sunnah.com's collection selector.",
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
        help="Seconds to wait between book-page requests. Default: 1.0",
    )
    parser.add_argument(
        "--max-books",
        type=int,
        help="Limit collection parsing to the first N books.",
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
        help="Omit the english key from each hadith object in the output JSON.",
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
