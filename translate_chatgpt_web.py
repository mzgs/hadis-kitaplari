#!/usr/bin/env python3

import json
from argparse import ArgumentParser
from pathlib import Path
import re
import urllib.error
import urllib.request


API_URL = "http://127.0.0.1:8787/api/reply"
DEFAULT_OUT_PATH = Path("out.json")
DEFAULT_MAX_APPEND_CHARS = 24_000
DEFAULT_TIMEOUT_SECONDS = 300
RANGE_FILE_RE = re.compile(r"^(\d+)-(\d+)\.json$")

PROMPT = """
Aşağıdaki tüm hadisleri Türkçeye çevir. 
Çeviri sade, doğru ve akıcı Türkçe olsun. 
Dini terimleri mümkünse klasik Türkçe kullanımına uygun çevir. 
(sallallahu aleyhi ve sellem) yerine (s.a.v.) kullan.
Gerekirse önemli kelimeler için kısa not ekle. 

"عن فلان" kalıplarını mümkün olduğunda "Falancadan rivayet edildiğine göre" veya "Falanca şöyle rivayet etmiştir" şeklinde çevir.
"قال" ifadesini bağlama göre "dedi ki", "şöyle buyurdu", "şöyle dedi" şeklinde çevir.
Hz. Peygamber için "Nebî (s.a.v.)" veya "Resûlullah (s.a.v.)" ifadelerini bağlama uygun şekilde kullan.
Çeviriler Diyanet, İSAM ve klasik Türkçe hadis tercümelerinin üslubuna yakın olsun.

Okuyucunun bilmeyeceği şahıslar, yerler, kabileler, olaylar ve kavramlar ilk geçtiği yerde çok kısa açıklamayla verilsin.
Tarihî bağlam kesin olarak biliniyorsa metnin içine eklenebilsin.
Arapça metinde kapalı bırakılan ancak hadis âlimlerinin ittifakla açıkladığı hususlar okuyucunun anlayacağı şekilde metne yedirilsin.

Türkçe karşılığı doğru olsa bile tercüme kokan, yapay ifadeler kullanma. Arapçadaki vurgu, hasr, ism-i tafdîl ve belagat inceliklerini koruyarak doğal, sade ve klasik hadis tercümesi üslubuna yakın Türkçe kur.
arapca bir kelimenin anlamini cumlede kaybetme ve dogal turkce klasik turkce hadis uslubu kullan.
Cogunlugun bildigi kelimeleri parantez icinde anlamlarini vermene gerek yok.
Output format, no markdown:
[{"tr":"<Turkish translation>","reference": ""}]

 



"""


def parse_args():
    parser = ArgumentParser(
        description="Send the translation prompt to the local ChatGPT web bridge."
    )
    parser.add_argument(
        "--book",
        type=Path,
        help="JSON book file whose hadith items should be appended to the prompt.",
    )
    parser.add_argument(
        "--hadiths",
        help="Comma-separated one-based hadith item indexes to include, e.g. 1,5,6.",
    )
    parser.add_argument(
        "--max-append-chars",
        type=int,
        default=DEFAULT_MAX_APPEND_CHARS,
        help=(
            "Maximum number of characters from the appended hadith JSON per "
            f"automatic batch. Defaults to {DEFAULT_MAX_APPEND_CHARS}."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Seconds to wait for each local ChatGPT bridge response. "
            f"Defaults to {DEFAULT_TIMEOUT_SECONDS}."
        ),
    )
    return parser.parse_args()


def parse_hadith_indexes(raw_indexes):
    if not raw_indexes:
        return None

    indexes = []
    for raw_index in raw_indexes.split(","):
        raw_index = raw_index.strip()
        if not raw_index:
            continue

        try:
            index = int(raw_index)
        except ValueError as exc:
            raise ValueError(f"Invalid hadith index: {raw_index!r}") from exc

        if index < 1:
            raise ValueError(f"Hadith indexes must be one-based: {index}")

        indexes.append(index)

    if not indexes:
        raise ValueError("--hadiths must include at least one index")

    return indexes


def collect_hadith_items(book_data):
    if isinstance(book_data, list):
        return book_data

    if not isinstance(book_data, dict):
        raise ValueError("Book JSON must be an object or list")

    if isinstance(book_data.get("content"), list):
        return book_data["content"]

    hadith_items = []
    for book in book_data.get("books", []):
        if isinstance(book, dict) and isinstance(book.get("content"), list):
            hadith_items.extend(book["content"])

    if not hadith_items:
        raise ValueError("Book JSON does not contain any hadith items")

    return hadith_items


def select_hadith_items(hadith_items, indexes):
    if indexes is None:
        indexes = range(1, len(hadith_items) + 1)

    selected_items = []
    for index in indexes:
        try:
            item = hadith_items[index - 1]
        except IndexError as exc:
            raise ValueError(
                f"Hadith index {index} is out of range; book has {len(hadith_items)} items"
            ) from exc

        if isinstance(item, dict):
            selected_item = {"index": index, **item}
        else:
            selected_item = {"index": index, "value": item}
        selected_items.append(selected_item)

    return selected_items


def build_translation_prompt(selected_items):
    hadiths_json = json.dumps(selected_items, ensure_ascii=False, indent=2)
    return (
        f"{PROMPT.rstrip()}\n\n"
        "Aşağıdaki JSON dizisindeki hadisleri çevir. "
        "Her sonuçta aynı reference değerini kullan.\n"
        f"{hadiths_json}\n"
    )


def build_prompt(book_path=None, raw_hadith_indexes=None):
    if raw_hadith_indexes and not book_path:
        raise ValueError("--hadiths can only be used with --book")

    if not book_path:
        return PROMPT, DEFAULT_OUT_PATH

    with open(book_path, encoding="utf-8") as book_file:
        book_data = json.load(book_file)

    hadith_items = collect_hadith_items(book_data)
    indexes = parse_hadith_indexes(raw_hadith_indexes)
    selected_items = select_hadith_items(hadith_items, indexes)

    prompt = build_translation_prompt(selected_items)
    output_path = Path("translations") / book_path.stem / "out.json"

    return prompt, output_path


def get_existing_ranges(output_dir):
    ranges = []
    if not output_dir.exists():
        return ranges

    for path in output_dir.iterdir():
        match = RANGE_FILE_RE.match(path.name)
        if not match or not path.is_file():
            continue

        start, end = (int(value) for value in match.groups())
        if start <= end:
            ranges.append((start, end, path))

    ranges.sort(key=lambda item: (item[0], item[1]))
    return ranges


def find_covering_range(index, ranges):
    for start, end, path in ranges:
        if start <= index <= end:
            return start, end, path
    return None


def is_covered(index, ranges):
    return find_covering_range(index, ranges) is not None


def build_auto_batch(hadith_items, start_index, existing_ranges, max_append_chars):
    selected_items = []
    current_index = start_index

    while current_index <= len(hadith_items):
        if is_covered(current_index, existing_ranges):
            break

        candidate_items = select_hadith_items(hadith_items, [current_index])
        next_items = selected_items + candidate_items
        appended_json = json.dumps(next_items, ensure_ascii=False, indent=2)

        if selected_items and len(appended_json) > max_append_chars:
            break

        selected_items = next_items
        current_index += 1

        if len(appended_json) > max_append_chars:
            break

    return selected_items


def load_book_items(book_path):
    with open(book_path, encoding="utf-8") as book_file:
        book_data = json.load(book_file)
    return collect_hadith_items(book_data)


def write_response(body, output_path):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = body

    if isinstance(data, dict) and "response" in data:
        data = data["response"]

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            pass

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        if isinstance(data, str):
            output_file.write(data)
            if not data.endswith("\n"):
                output_file.write("\n")
        else:
            json.dump(data, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")


def request_translation(prompt, output_path, timeout):
    payload = json.dumps({"prompt": prompt}).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        print(body)
        write_response(body, output_path)
        print(f"Wrote response to {output_path}")


def run_auto_batches(book_path, max_append_chars, timeout):
    if max_append_chars < 1:
        raise ValueError("--max-append-chars must be greater than zero")
    if timeout <= 0:
        raise ValueError("--timeout must be greater than zero")

    hadith_items = load_book_items(book_path)
    output_dir = Path("translations") / book_path.stem
    existing_ranges = get_existing_ranges(output_dir)
    current_index = 1

    while current_index <= len(hadith_items):
        covering_range = find_covering_range(current_index, existing_ranges)
        if covering_range:
            _, end, path = covering_range
            print(f"Skipping {path}; covers {current_index}-{end}")
            current_index = end + 1
            continue

        selected_items = build_auto_batch(
            hadith_items,
            current_index,
            existing_ranges,
            max_append_chars,
        )
        if not selected_items:
            current_index += 1
            continue

        start_index = selected_items[0]["index"]
        end_index = selected_items[-1]["index"]
        output_path = output_dir / f"{start_index}-{end_index}.json"
        if output_path.exists():
            print(f"Skipping {output_path}; already exists")
            existing_ranges.append((start_index, end_index, output_path))
            existing_ranges.sort(key=lambda item: (item[0], item[1]))
            current_index = end_index + 1
            continue

        appended_json = json.dumps(selected_items, ensure_ascii=False, indent=2)
        print(
            f"Translating {start_index}-{end_index} "
            f"({len(selected_items)} hadiths, {len(appended_json)} appended chars)"
        )
        prompt = build_translation_prompt(selected_items)
        request_translation(prompt, output_path, timeout)

        existing_ranges.append((start_index, end_index, output_path))
        existing_ranges.sort(key=lambda item: (item[0], item[1]))
        current_index = end_index + 1


def main():
    args = parse_args()

    if args.book and not args.hadiths:
        try:
            run_auto_batches(args.book, args.max_append_chars, args.timeout)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Failed to run automatic batches: {exc}")
            raise SystemExit(1) from exc
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        except urllib.error.URLError as exc:
            print(f"Request failed: {exc.reason}")
        return

    try:
        prompt, output_path = build_prompt(args.book, args.hadiths)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to build prompt: {exc}")
        raise SystemExit(1) from exc

    try:
        request_translation(prompt, output_path, args.timeout)
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc.reason}")


if __name__ == "__main__":
    main()
