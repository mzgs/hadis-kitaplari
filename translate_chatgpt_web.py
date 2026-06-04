#!/usr/bin/env python3

import json
from argparse import ArgumentParser
from pathlib import Path
import urllib.error
import urllib.request


API_URL = "http://127.0.0.1:8787/api/reply"
DEFAULT_OUT_PATH = Path("out.json")
DEFAULT_TIMEOUT_SECONDS = 300

PROMPT = """
Aşağıdaki hadisi Türkçeye çevir.

Çeviri doğal, akıcı ve doğru Türkçe olsun. Klasik hadis tercümesi üslubuna yakın kal, ancak yapay ve tercüme kokan ifadeler kullanma.

* (صلى الله عليه وسلم) → (s.a.v.)
* Hz. Peygamber için bağlama göre "Resûlullah (s.a.v.)" veya "Nebî (s.a.v.)" kullan.
* Rivayet kalıplarını doğal Türkçe ile aktar.
* İsnadları (rivayet zincirlerini) okuyucunun rahat takip edebileceği şekilde çevir; uzun ravi zincirlerini kelime kelime çevirmek zorunda değilsin.
* Siyak ve sibakı dikkate al.
* Arapça metnin muradını doğru yansıt.
* Tartışmalı, spekülatif veya metinde temeli olmayan yorumlar ekleme.
* Gerekirse kısa açıklamalar ekleyebilirsin, ancak tercüme tefsire dönüşmesin.
* Yerleşik İslâmî terimleri anlam kaybına yol açacaksa koru.

Kurallar arasında çatışma oluşursa öncelik sırası şöyledir:

1. Anlamın doğruluğu
2. Hadisin muradının korunması
3. Doğal ve akıcı Türkçe
4. Klasik hadis tercümesi üslubu
5. Lafzî sadakat

Lafzî sadakat doğal Türkçeyi bozuyorsa, anlamı korumak şartıyla doğal Türkçe tercih edilebilir.

"عن فلان" kalıplarını mümkün olduğunda "Falancadan rivayet edildiğine göre" veya "Falanca şöyle rivayet etmiştir" şeklinde çevir.
"قال" ifadesini bağlama göre "dedi ki", "şöyle buyurdu", "şöyle dedi" şeklinde çevir.


Soru ve cevap arasında anlam ilişkisini gözet. Arapça lafız zahiren bir kavramı (İslâm, iman, ihsan vb.) sorsa bile, cevaptan açıkça anlaşılıyorsa Türkçede muradı yansıtacak şekilde tercüme et. Gerektiğinde lafzî tercüme yerine, kastedilen anlamı ver.

Hitapları Türkçe hadis tercümesi geleneğine uygun aktar. "يا رسول الله", "يا نبي الله" gibi ifadeleri lafzen "Ey Resûlullah", "Ey Allah'ın Nebîsi" şeklinde çevirmek yerine mümkün olduğunda "Yâ Resûlallah", "Yâ Nebiyyallah" şeklinde koru.

Hadisteki vurgu ve derecelendirmeleri koru. Bir sıfatın en yüksek derecesini, fazilet sıralamasını veya zirve hâlini ifade eden lafızları, sadece genel bir artış veya çoğalma anlamına indirgeme. Tercümede metnin vurguladığı üstünlük derecesi açıkça hissedilsin

Çeviri sırasında yalnızca lafzı değil, metnin işaret ettiği tarihî ve ilmî referansları da dikkate al. Hadis âlimlerinin ve tarih kaynaklarının ittifakla belirlediği kişi, olay, yer ve kavramlar mümkün olduğunca yerleşik isimleriyle anılsın; okuyucunun bunları ayrıca araştırmasına gerek bırakmayacak ölçüde kısa ve doğal açıklamalar eklensin


output format json, no markdown:
{
"tr":"<Turkish translation>",
"reference":""
}
 
 
 

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
        help=(
            "Comma-separated one-based hadith item indexes or ranges to include, "
            "e.g. 1,5,6 or 1-4."
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate existing per-hadith JSON files instead of skipping them.",
    )
    return parser.parse_args()


def parse_hadith_indexes(raw_indexes):
    if not raw_indexes:
        return None

    indexes = []
    for raw_part in raw_indexes.split(","):
        raw_part = raw_part.strip()
        if not raw_part:
            continue

        if "-" in raw_part:
            raw_start, separator, raw_end = raw_part.partition("-")
            if not raw_start.strip() or not raw_end.strip() or separator != "-":
                raise ValueError(f"Invalid hadith range: {raw_part!r}")

            try:
                start = int(raw_start)
                end = int(raw_end)
            except ValueError as exc:
                raise ValueError(f"Invalid hadith range: {raw_part!r}") from exc

            if start < 1 or end < 1:
                raise ValueError(f"Hadith indexes must be one-based: {raw_part}")
            if start > end:
                raise ValueError(f"Hadith range start must be <= end: {raw_part}")

            indexes.extend(range(start, end + 1))
            continue

        try:
            index = int(raw_part)
        except ValueError as exc:
            raise ValueError(f"Invalid hadith index: {raw_part!r}") from exc

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
        f"\n{PROMPT.rstrip()}\n\n"
        f"{hadiths_json}"
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


def run_hadith_translations(book_path, raw_hadith_indexes, timeout, force=False):
    if timeout <= 0:
        raise ValueError("--timeout must be greater than zero")

    hadith_items = load_book_items(book_path)
    output_dir = Path("translations") / book_path.stem
    indexes = parse_hadith_indexes(raw_hadith_indexes)
    if indexes is None:
        indexes = range(1, len(hadith_items) + 1)

    for index in indexes:
        if index > len(hadith_items):
            raise ValueError(
                f"Hadith index {index} is out of range; book has {len(hadith_items)} items"
            )

    for index in indexes:
        output_path = output_dir / f"{index}.json"
        if output_path.exists() and not force:
            print(f"Skipping {output_path}; already exists")
            continue

        selected_items = select_hadith_items(hadith_items, [index])
        if output_path.exists():
            print(f"Recreating {output_path}")
        else:
            print(f"Translating {index}")
        prompt = build_translation_prompt(selected_items)
        request_translation(prompt, output_path, timeout)


def main():
    args = parse_args()

    if args.book:
        try:
            run_hadith_translations(args.book, args.hadiths, args.timeout, args.force)
        except KeyboardInterrupt:
            print("\nStopped by user. Current in-progress hadith was not saved.")
            raise SystemExit(130)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Failed to run hadith translations: {exc}")
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
    except KeyboardInterrupt:
        print("\nStopped by user. Current in-progress request was not saved.")
        raise SystemExit(130)
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc.reason}")


if __name__ == "__main__":
    main()
