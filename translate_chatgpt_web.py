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
MULTI_PROMPT_MAX_CHARS = 18000
STOP_RESPONSE_MODELS = {"gpt-5-3-mini"}
REQUIRED_TRANSLATION_FIELDS = {"tr", "reference"}
OPTIONAL_TRANSLATION_FIELDS = {"grade"}
TRANSLATION_FIELDS = REQUIRED_TRANSLATION_FIELDS | OPTIONAL_TRANSLATION_FIELDS


class StopTranslation(Exception):
    pass


class IncompleteMultiTranslation(ValueError):
    def __init__(self, expected_count, received_count, missing_positions):
        self.missing_positions = tuple(missing_positions)
        saved_count = expected_count - len(self.missing_positions)
        super().__init__(
            "Multi translation response count does not match request: "
            f"expected {expected_count}, got {received_count}; "
            f"saved {saved_count}, missing {len(self.missing_positions)}"
        )


PROMPT = """
Aşağıdaki hadisleri doğal Türkiye klsik turkce hadis usulu ile cevir. Kelime kelime tercümeden kaçın. Gereksiz resmî, edebî veya çeviri kokan ifadeler kullanma.

kurallar:
- Peygamber Efendimizden bahsedildiğinde (sav), sahabelerden bahsedildiğinde (ra), büyük İslam âlimlerinden bahsedildiğinde (rh.) ekle. 

Output JSON only:

[
{
"tr": "<Türkçe çeviri>",
"reference": "<source reference>"
}
]

"""

PROMPT2 = """
İlk çeviriyi Arapça metinle yeniden karşılaştır. Eksiltme, ekleme, yanlış özne,
yanlış zamir, anlam kayması, zayıflatılmış vurgu, bozuk Türkçe veya tutarsız
terim varsa düzelt. Sadece doğal ifade uğruna anlamı değiştirme. Son cevapta
yalnızca ana promptta tanımlanan JSON çıktısını döndür.
"""

MULTI_PROMPT_INSTRUCTIONS = """
Birden fazla hadis verildiyse, her hadis için ayrı bir JSON nesnesi üret ve
nesneleri girişteki sırayla aynı JSON array içinde döndür. Eksik, fazla veya
birleştirilmiş kayıt üretme.
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
    parser.add_argument(
        "--multi",
        action="store_true",
        help=(
            "Translate multiple hadith items in one request, batching prompts up "
            f"to {MULTI_PROMPT_MAX_CHARS} characters."
        ),
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


def build_translation_prompt(selected_items, no_english=False, multi=False):
    prompt_items = omit_english_fields(selected_items) if no_english else selected_items
    hadiths_json = json.dumps(prompt_items, ensure_ascii=False, indent=2)
    multi_instructions = (
        f"\n\n{MULTI_PROMPT_INSTRUCTIONS.strip()}" if multi else ""
    )
    return (
        f"\n{PROMPT.rstrip()}{multi_instructions}\n\n"
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
    if not tr_match or not reference_match:
        raise ValueError("Could not recover translation fields from model response")

    fields = {
        "tr": decode_json_string_content(tr_match.group(1)),
        "reference": decode_json_string_content(reference_match.group(1)),
    }
    if grade_match:
        fields["grade"] = decode_json_string_content(grade_match.group(1))
    return fields


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
    missing_required = sorted(REQUIRED_TRANSLATION_FIELDS - fields)
    extra = sorted(fields - TRANSLATION_FIELDS)
    if missing_required or extra:
        raise ValueError(
            "Translation response must contain tr and reference; grade is optional; "
            f"missing_required={missing_required}, extra={extra}"
        )

    for field in fields:
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


def parse_response_payload(body):
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
    return data, raw_model_response


def write_translation_file(data, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(data, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")


def write_response(body, output_path, expected_reference=None):
    data, raw_model_response = parse_response_payload(body)
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

    write_translation_file(data, output_path)


def write_multi_response(body, output_paths, expected_references):
    if expected_references is None:
        expected_references = [None] * len(output_paths)
    if len(expected_references) != len(output_paths):
        raise ValueError(
            "Expected reference count does not match output path count: "
            f"expected {len(output_paths)}, got {len(expected_references)}"
        )

    data, raw_model_response = parse_response_payload(body)

    if isinstance(data, dict) and len(output_paths) == 1:
        data = [data]
    if not isinstance(data, list):
        if raw_model_response is not None and len(output_paths) == 1:
            data = [extract_translation_fields(raw_model_response)]
        else:
            raise ValueError("Multi translation response must be a JSON array")
    if len(data) != len(output_paths):
        if len(data) > len(output_paths):
            raise ValueError(
                "Multi translation response count does not match request: "
                f"expected {len(output_paths)}, got {len(data)}"
            )

        unmatched_positions = set(range(len(output_paths)))
        matched_items = []
        for item in data:
            item = validate_translation(item)
            matching_positions = [
                position
                for position in unmatched_positions
                if expected_references[position] is not None
                and references_match(
                    item["reference"], expected_references[position]
                )
            ]
            if len(matching_positions) != 1:
                raise ValueError(
                    "Could not uniquely match partial multi translation response "
                    f"reference {item['reference']!r} to the request"
                )

            position = matching_positions[0]
            unmatched_positions.remove(position)
            matched_items.append(
                (
                    validate_translation(item, expected_references[position]),
                    output_paths[position],
                )
            )

        for item, output_path in matched_items:
            write_translation_file(item, output_path)

        raise IncompleteMultiTranslation(
            len(output_paths),
            len(data),
            sorted(unmatched_positions),
        )

    validated_items = [
        validate_translation(item, expected_reference)
        for item, expected_reference in zip(data, expected_references)
    ]
    for item, output_path in zip(validated_items, output_paths):
        write_translation_file(item, output_path)


def request_translation(
    prompt,
    output_path,
    timeout,
    enable_prompt2=False,
    expected_reference=None,
    output_paths=None,
    expected_references=None,
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
        if output_paths is not None:
            write_multi_response(body, output_paths, expected_references)
            print(f"Wrote {len(output_paths)} responses")
        else:
            write_response(body, output_path, expected_reference)
            print(f"Wrote response to {output_path}")


def build_multi_batches(work_items, no_english=False):
    batches = []
    current_batch = []
    current_prompt = ""

    for work_item in work_items:
        candidate_batch = current_batch + [work_item]
        candidate_prompt = build_translation_prompt(
            [item["selected_item"] for item in candidate_batch],
            no_english,
            multi=True,
        )

        if len(candidate_prompt) > MULTI_PROMPT_MAX_CHARS:
            if not current_batch:
                raise ValueError(
                    f"Hadith {work_item['index']} prompt is "
                    f"{len(candidate_prompt)} characters, above "
                    f"{MULTI_PROMPT_MAX_CHARS}"
                )
            batches.append((current_batch, current_prompt))
            current_batch = [work_item]
            current_prompt = build_translation_prompt(
                [work_item["selected_item"]],
                no_english,
                multi=True,
            )
            if len(current_prompt) > MULTI_PROMPT_MAX_CHARS:
                raise ValueError(
                    f"Hadith {work_item['index']} prompt is "
                    f"{len(current_prompt)} characters, above "
                    f"{MULTI_PROMPT_MAX_CHARS}"
                )
            continue

        current_batch = candidate_batch
        current_prompt = candidate_prompt

    if current_batch:
        batches.append((current_batch, current_prompt))

    return batches


def translate_multi_batch(
    batch,
    timeout,
    enable_prompt2=False,
    no_english=False,
    prompt=None,
):
    if prompt is None:
        prompt = build_translation_prompt(
            [item["selected_item"] for item in batch],
            no_english,
            multi=True,
        )

    indexes_text = ", ".join(str(item["index"]) for item in batch)
    print(f"Translating batch [{indexes_text}] ({len(prompt)} chars)")

    try:
        request_translation(
            prompt,
            None,
            timeout,
            enable_prompt2,
            output_paths=[item["output_path"] for item in batch],
            expected_references=[
                item["expected_reference"] for item in batch
            ],
        )
    except IncompleteMultiTranslation as exc:
        missing_batch = [batch[position] for position in exc.missing_positions]
        print(f"{exc}; retrying missing hadiths")

        if len(missing_batch) == len(batch):
            if len(batch) == 1:
                raise
            midpoint = len(batch) // 2
            translate_multi_batch(
                batch[:midpoint],
                timeout,
                enable_prompt2,
                no_english,
            )
            translate_multi_batch(
                batch[midpoint:],
                timeout,
                enable_prompt2,
                no_english,
            )
            return

        translate_multi_batch(
            missing_batch,
            timeout,
            enable_prompt2,
            no_english,
        )


def run_hadith_translations(
    book_path,
    raw_hadith_indexes,
    timeout,
    force=False,
    enable_prompt2=False,
    no_english=False,
    multi=False,
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

    if multi:
        work_items = []
        for index in indexes:
            output_path = output_dir / f"{index}.json"
            if output_path.exists() and not force:
                print(f"Skipping {output_path}; already exists")
                continue

            selected_items = select_hadith_items(hadith_items, [index])
            if output_path.exists():
                print(f"Will recreate {output_path}")
            else:
                print(f"Will translate {index}")
            work_items.append(
                {
                    "index": index,
                    "output_path": output_path,
                    "selected_item": selected_items[0],
                    "expected_reference": (
                        selected_items[0].get("reference")
                        if isinstance(selected_items[0], dict)
                        else None
                    ),
                }
            )

        if not work_items:
            print("No hadiths to translate")
            return

        for batch, prompt in build_multi_batches(work_items, no_english):
            translate_multi_batch(
                batch,
                timeout,
                enable_prompt2,
                no_english,
                prompt,
            )
        return

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

    if args.multi and not args.book:
        print("--multi can only be used with --book")
        raise SystemExit(1)

    if args.book:
        try:
            run_hadith_translations(
                args.book,
                args.hadiths,
                args.timeout,
                args.force,
                args.enable_prompt2,
                args.no_english,
                args.multi,
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
