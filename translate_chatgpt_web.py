#!/usr/bin/env python3

import json
from argparse import ArgumentParser
from pathlib import Path
import re
import unicodedata
import urllib.error
import urllib.request

import json_repair


API_URL = "http://127.0.0.1:8787/api/reply"
DEFAULT_OUT_PATH = Path("out.json")
DEFAULT_TIMEOUT_SECONDS = 300
STOP_RESPONSE_MODELS = {"gpt-5-3-mini"}
TRANSLATION_FIELDS = {"tr", "reference", "grade"}


class StopTranslation(Exception):
    pass

PROMPT = """
Aşağıdaki hadisi doğal Türkiye Türkçesiyle çevir. Kelime kelime tercümeden kaçın. Gereksiz resmî, edebî veya çeviri kokan ifadeler kullanma.

kurallar:
- Peygamber Efendimizden bahsedildiğinde (s.a.v.), sahabelerden bahsedildiğinde (r.a.), büyük İslam âlimlerinden bahsedildiğinde (rh.) ekle. 
- Canım kudret elinde olan Allah’a → Canım elinde olan Allah’a
- Kişi isimlerini Türkiye'de yaygın kullanılan İslami yazımla Türkçeleştir (Enes, Ebu Hureyre, Abdullah b. Abbas, İmam Buhârî vb.).
- Dini ve ahlaki kavramları koru; anlamı daraltan modern karşılıklar kullanma.
- "reference" alanını kaynakta verildiği biçimiyle aynen koru; tercüme etme veya yazımını değiştirme.

Output JSON only:

{
  "tr": "<Türkçe çeviri>",
  "reference": "<source reference>",
  "grade": "<Âlim - Hüküm>"
}
"""

PROMPT2 = """
İlk çeviriyi Arapça metinle yeniden karşılaştır. Eksiltme, ekleme, yanlış özne,
yanlış zamir, anlam kayması, zayıflatılmış vurgu, bozuk Türkçe veya tutarsız
terim varsa düzelt. Sadece doğal ifade uğruna anlamı değiştirme. Son cevapta
yalnızca ana promptta tanımlanan üç alanlı JSON nesnesini döndür.
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
    parser.add_argument(
        "--enable-prompt2",
        dest="enable_prompt2",
        action="store_true",
        help="Include the secondary prompt as prompt2 in the bridge API payload.",
    )
    parser.add_argument(
        "--no-english",
        action="store_true",
        help="Omit English translation/context fields from the prompt payload.",
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


def omit_english_fields(value):
    if isinstance(value, list):
        return [omit_english_fields(item) for item in value]

    if isinstance(value, dict):
        return {
            key: omit_english_fields(item)
            for key, item in value.items()
            if key.lower() != "english"
        }

    return value


def build_translation_prompt(selected_items, no_english=False):
    prompt_items = omit_english_fields(selected_items) if no_english else selected_items
    hadiths_json = json.dumps(prompt_items, ensure_ascii=False, indent=2)
    return (
        f"\n{PROMPT.rstrip()}\n\n"
        f"{hadiths_json}"
    )


def build_prompt(book_path=None, raw_hadith_indexes=None, no_english=False):
    if raw_hadith_indexes and not book_path:
        raise ValueError("--hadiths can only be used with --book")

    if not book_path:
        return PROMPT, DEFAULT_OUT_PATH

    with open(book_path, encoding="utf-8") as book_file:
        book_data = json.load(book_file)

    hadith_items = collect_hadith_items(book_data)
    indexes = parse_hadith_indexes(raw_hadith_indexes)
    selected_items = select_hadith_items(hadith_items, indexes)

    prompt = build_translation_prompt(selected_items, no_english)
    output_path = Path("translations") / book_path.stem / "out.json"

    return prompt, output_path


def load_book_items(book_path):
    with open(book_path, encoding="utf-8") as book_file:
        book_data = json.load(book_file)
    return collect_hadith_items(book_data)


def parse_repaired_json(value, context):
    if not isinstance(value, str):
        return value

    try:
        return json_repair.loads(value)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(f"Could not parse or repair {context} as JSON") from exc


def decode_json_string_content(value):
    escaped = []
    preceding_backslashes = 0

    for character in value:
        if character == '"' and preceding_backslashes % 2 == 0:
            escaped.append("\\")
        escaped.append(character)

        if character == "\\":
            preceding_backslashes += 1
        else:
            preceding_backslashes = 0

    try:
        return json.loads(f'"{"".join(escaped)}"')
    except json.JSONDecodeError as exc:
        raise ValueError("Could not decode repaired translation field") from exc


def extract_translation_fields(raw_response):
    if not isinstance(raw_response, str):
        raise ValueError("Translation fallback requires a string response")

    tr_match = re.search(
        r'"tr"\s*:\s*"(.*)"\s*,\s*"reference"\s*:',
        raw_response,
        flags=re.DOTALL,
    )
    reference_match = re.search(
        r'"reference"\s*:\s*"((?:\\.|[^"\\])*)"',
        raw_response,
        flags=re.DOTALL,
    )
    grade_match = re.search(
        r'"grade"\s*:\s*"((?:\\.|[^"\\])*)"',
        raw_response,
        flags=re.DOTALL,
    )
    if not tr_match or not reference_match or not grade_match:
        raise ValueError("Could not recover translation fields from model response")

    return {
        "tr": decode_json_string_content(tr_match.group(1)),
        "reference": decode_json_string_content(reference_match.group(1)),
        "grade": decode_json_string_content(grade_match.group(1)),
    }


def normalize_reference_text(reference):
    normalized = unicodedata.normalize("NFKD", reference)
    normalized = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    normalized = normalized.casefold().replace("ı", "i")
    normalized = re.sub(r"\b(?:al|el|as|at)\b", " ", normalized)
    normalized = normalized.replace("kh", "h")
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def references_match(actual_reference, expected_reference):
    actual_numbers = re.findall(r"\d+", actual_reference)
    expected_numbers = re.findall(r"\d+", expected_reference)
    if actual_numbers != expected_numbers:
        return False

    return normalize_reference_text(actual_reference) == normalize_reference_text(
        expected_reference
    )


def validate_translation(data, expected_reference=None):
    if not isinstance(data, dict):
        raise ValueError("Translation response must be a JSON object")

    fields = set(data)
    if fields != TRANSLATION_FIELDS:
        missing = sorted(TRANSLATION_FIELDS - fields)
        extra = sorted(fields - TRANSLATION_FIELDS)
        raise ValueError(
            "Translation response must contain exactly tr, reference, and grade; "
            f"missing={missing}, extra={extra}"
        )

    for field in TRANSLATION_FIELDS:
        if not isinstance(data[field], str):
            raise ValueError(f"Translation field {field!r} must be a string")

    if not data["tr"].strip():
        raise ValueError("Translation field 'tr' must not be empty")
    if not data["reference"].strip():
        raise ValueError("Translation field 'reference' must not be empty")
    if expected_reference is not None:
        if not references_match(data["reference"], expected_reference):
            raise ValueError(
                "Translation reference does not match the source: "
                f"expected {expected_reference!r}, got {data['reference']!r}"
            )
        data["reference"] = expected_reference

    return data


def write_response(body, output_path, expected_reference=None):
    raw_bridge_response = body if isinstance(body, str) else None
    data = parse_repaired_json(body, "bridge response")
    raw_model_response = raw_bridge_response

    if isinstance(data, dict):
        response_model = data.get("model")
        if response_model in STOP_RESPONSE_MODELS:
            raise StopTranslation(
                f"Stop reason: response model {response_model} is not allowed; "
                "response was not saved."
            )

        if "response" in data:
            data = data["response"]
            raw_model_response = data if isinstance(data, str) else None

    data = parse_repaired_json(data, "model response")
    try:
        data = validate_translation(data, expected_reference)
    except ValueError as validation_error:
        if raw_model_response is None:
            raise
        try:
            data = extract_translation_fields(raw_model_response)
        except ValueError:
            raise validation_error
        data = validate_translation(data, expected_reference)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(data, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")


def request_translation(
    prompt,
    output_path,
    timeout,
    enable_prompt2=False,
    expected_reference=None,
):
    request_payload = {"prompt": prompt}
    if enable_prompt2:
        request_payload["prompt2"] = PROMPT2

    payload = json.dumps(request_payload).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        print(body)
        write_response(body, output_path, expected_reference)
        print(f"Wrote response to {output_path}")


def run_hadith_translations(
    book_path,
    raw_hadith_indexes,
    timeout,
    force=False,
    enable_prompt2=False,
    no_english=False,
):
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
        prompt = build_translation_prompt(selected_items, no_english)
        expected_reference = (
            selected_items[0].get("reference")
            if isinstance(selected_items[0], dict)
            else None
        )
        request_translation(
            prompt,
            output_path,
            timeout,
            enable_prompt2,
            expected_reference,
        )


def main():
    args = parse_args()

    if args.book:
        try:
            run_hadith_translations(
                args.book,
                args.hadiths,
                args.timeout,
                args.force,
                args.enable_prompt2,
                args.no_english,
            )
        except KeyboardInterrupt:
            print("\nStopped by user. Current in-progress hadith was not saved.")
            raise SystemExit(130)
        except StopTranslation as exc:
            print(exc)
            raise SystemExit(1) from exc
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Failed to run hadith translations: {exc}")
            raise SystemExit(1) from exc
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        except urllib.error.URLError as exc:
            print(f"Request failed: {exc.reason}")
        return

    try:
        prompt, output_path = build_prompt(args.book, args.hadiths, args.no_english)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to build prompt: {exc}")
        raise SystemExit(1) from exc

    try:
        request_translation(prompt, output_path, args.timeout, args.enable_prompt2)
    except KeyboardInterrupt:
        print("\nStopped by user. Current in-progress request was not saved.")
        raise SystemExit(130)
    except StopTranslation as exc:
        print(exc)
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(f"Invalid translation response: {exc}")
        raise SystemExit(1) from exc
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc.reason}")


if __name__ == "__main__":
    main()
