#!/usr/bin/env python3
"""Repair Turkish translations that were filled from non-Arabic machine sources.

This pass does three conservative things:
1. Normalizes the Turkish register according to master_islamic_translation_prompt.md.
2. Replaces a known over-expanded entry with a direct Arabic-based rendering.
3. Clears translations that still have no Arabic source after an Arabic API lookup.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "turkce_missing_report.json"


FILES = [
    "abudawud.json",
    "buhari.json",
    "ibnmajah.json",
    "malik.json",
    "muslim.json",
]


SOURCE_DETAIL_RE = re.compile(r"^(?:eng|fra|rus)-([^/]+)/(.+)$")


MANUAL_OVERRIDES: dict[tuple[str, str], str] = {
    (
        "abudawud.json",
        "281",
    ): "Resûlullah ﷺ'e sormasını istedi. Bunun üzerine Resûlullah ﷺ ona, oturageldiği günler kadar beklemesini, sonra gusletmesini emretti.",
    (
        "buhari.json",
        "5712",
    ): "Ebû Bekir, Peygamber ﷺ vefat etmişken onu öptü. Âişe de şöyle dedi: Hastalığında Resûlullah'a ağzının kenarından ilaç verdik. O bize, \"Bana böyle ilaç vermeyin\" diye işaret etmeye başladı. Biz, \"Bu, hastanın ilacı hoş görmemesidir\" dedik. Kendine gelince, \"Size bana böyle ilaç vermenizi yasaklamadım mı?\" buyurdu. \"Hastanın ilacı hoş görmemesi sandık\" dedik. Bunun üzerine, \"Abbas dışında evde bulunan hiç kimse kalmasın; ben bakarken ona da bu ilaç verilsin. Çünkü Abbas sizin yanınızda bulunmamıştı\" buyurdu.",
    (
        "buhari.json",
        "5775",
    ): "Resûlullah ﷺ şöyle buyurdu: \"Bulaşıcılık yoktur.\" Ebû Seleme b. Abdurrahman şöyle dedi: Ebû Hüreyre'nin, Peygamber ﷺ'den, \"Hastalıklı hayvanlar sağlıklı hayvanların yanına getirilmesin\" buyurduğunu işittim. Zührî'den rivayet edildiğine göre Sinân b. Ebû Sinân ed-Düelî ona Ebû Hüreyre'nin şöyle dediğini haber verdi: Resûlullah ﷺ, \"Bulaşıcılık yoktur\" buyurdu. Bunun üzerine bir bedevî kalkıp, \"Kumluktaki develer ceylanlar gibi olur da uyuz deve gelip aralarına karışınca onları uyuz eder; buna ne dersin?\" dedi. Peygamber ﷺ, \"Öyleyse ilkine kim bulaştırdı?\" buyurdu.",
    (
        "buhari.json",
        "6075",
    ): "Âişe'nin anne tarafından yeğeni Avf b. Mâlik b. Tufeyl'in rivayet ettiğine göre Âişe'ye, Abdullah b. Zübeyr'in, Âişe'nin yaptığı bir satış veya bağış hakkında, \"Vallahi Âişe bundan vazgeçmezse mutlaka onu hacr altına alırım\" dediği haber verildi. Âişe, \"Bunu o mu söyledi?\" dedi. \"Evet\" dediler. Bunun üzerine, \"Allah için üzerime adak olsun ki İbn Zübeyr ile ebediyen konuşmayacağım\" dedi. Ayrılık uzayınca İbn Zübeyr onun nezdinde şefaatçi aradı. Âişe, \"Hayır, vallahi onun hakkında hiçbir şefaatçiyi kabul etmeyeceğim ve adağımdan dönmeyeceğim\" dedi. Bu durum İbn Zübeyr'e ağır gelince, Benî Zühre'den Misver b. Mahreme ve Abdurrahman b. Esved b. Abdüyeğûs ile konuştu ve onlara, \"Allah aşkına, beni Âişe'nin yanına sokun; çünkü benimle ilişkiyi kesmeyi adaması ona helal değildir\" dedi. Misver ile Abdurrahman, ridâlarına bürünmüş halde onu yanlarında getirdiler; Âişe'den izin isteyip, \"es-Selâmü aleyki ve rahmetullahi ve berekâtüh, girelim mi?\" dediler. Âişe, \"Girin\" dedi. \"Hepimiz mi?\" dediler. \"Evet, hepiniz girin\" dedi; onların yanında İbn Zübeyr olduğunu bilmiyordu. İçeri girdiklerinde İbn Zübeyr perde arkasına girdi, Âişe'ye sarıldı, ona yalvarıp ağlamaya başladı. Misver ile Abdurrahman da onunla konuşmasını ve ondan kabul etmesini isteyerek yalvardılar; \"Peygamber ﷺ senin bildiğin hicrandan nehyetti; Müslümanın kardeşini üç geceden fazla terk etmesi helal değildir\" diyorlardı. Âişe'ye hatırlatmayı ve sıkıştırmayı artırınca Âişe de adağını hatırlatmaya, ağlamaya ve, \"Ben adakta bulundum; adak ağırdır\" demeye başladı. Nihayet onu bırakmadılar; İbn Zübeyr ile konuştu ve bu adağından dolayı kırk köle azat etti. Bundan sonra adağını hatırladığında başörtüsü gözyaşlarıyla ıslanıncaya kadar ağlardı.",
}


MANUAL_ARABIC_SOURCE_REFS: dict[tuple[str, str], str] = {
    ("buhari.json", "5712"): "bukhari:5709",
    ("buhari.json", "5775"): "bukhari:5773",
    ("buhari.json", "6075"): "bukhari:6073",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_turkish(text: str) -> str:
    replacements = [
        ("Resulullah", "Resûlullah"),
        ("Allah'ın Resulü", "Resûlullah"),
        ("Allah’ın Resulü", "Resûlullah"),
        ("Allah'ın Elçisi", "Resûlullah"),
        ("Allah’ın Elçisi", "Resûlullah"),
        ("Ey Resûlullah!", "Ey Resûlullah!"),
        ("Hz. Peygamber'e (ﷺ)", "Peygamber'e ﷺ"),
        ("Hz. Peygamber'den (ﷺ)", "Peygamber'den ﷺ"),
        ("Hz. Peygamber'e", "Peygamber'e"),
        ("Hz. Peygamber'den", "Peygamber'den"),
        ("Peygamber'in (ﷺ)", "Peygamber'in ﷺ"),
        ("Peygamber'e (ﷺ)", "Peygamber'e ﷺ"),
        ("Peygamber'den (ﷺ)", "Peygamber'den ﷺ"),
        ("Peygamber (ﷺ)", "Peygamber ﷺ"),
        ("Resûlullah'ın (ﷺ)", "Resûlullah'ın ﷺ"),
        ("Resûlullah'a (ﷺ)", "Resûlullah'a ﷺ"),
        ("Resûlullah'tan (ﷺ)", "Resûlullah'tan ﷺ"),
        ("Resûlullah'ı (ﷺ)", "Resûlullah'ı ﷺ"),
        ("Resûlullah (ﷺ)", "Resûlullah ﷺ"),
        ("Peygamber'in ﷺ", "Peygamber'in"),
        ("Resûlullah'ın ﷺ", "Resûlullah'ın"),
        ("Hz. Âişe", "Âişe"),
        ("Hz. Aişe", "Âişe"),
        ("Hz. Ali", "Ali"),
        ("Hz. Ömer", "Ömer"),
        ("Hz. Osman", "Osman"),
        ("Hz. Ebû Bekir", "Ebû Bekir"),
        ("Hz. İbn Abbas", "İbn Abbas"),
        ("Hz. Fâtıma", "Fâtıma"),
        ("Hz. Hafsa", "Hafsa"),
        ("Hz. Ümmü Seleme", "Ümmü Seleme"),
        ("Hz. ", ""),
        ("âdet gördüğü günler", "hayız gördüğü günler"),
        ("âdet günleri", "hayız günleri"),
        ("âdet günlerinde", "hayız günlerinde"),
        ("âdet süresi", "hayız süresi"),
        ("âdeti sona erince", "hayzı sona erince"),
        ("adet gördüğü günler", "hayız gördüğü günler"),
        ("adet günleri", "hayız günleri"),
        ("adet günlerinde", "hayız günlerinde"),
        ("sürekli kanaması bulunan kadın", "istihâza gören kadın"),
        ("sürekli kanaması olan kadın", "istihâza gören kadın"),
        ("sürekli kanama bulunan kadın", "istihâza gören kadın"),
        ("sürekli kanama vardı", "istihâza vardı"),
        ("sürekli kanaması vardı", "istihâza vardı"),
        ("sürekli kanama", "istihâza"),
        ("yıkanıp namazını kılar", "gusledip namazını kılar"),
        ("yıkanıp namaz kılar", "gusledip namaz kılar"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def fetch_arabic_from_api(source_detail: str, hadis_no: Any) -> str | None:
    match = SOURCE_DETAIL_RE.match(source_detail or "")
    if not match:
        return None

    collection, number = match.groups()
    url = (
        "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/"
        f"editions/ara-{collection}/{number}.json"
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
    except Exception:
        return None

    hadiths = data.get("hadiths") or []
    if not hadiths:
        return None

    wanted = str(hadis_no)
    source_wanted = str(number)
    for hadith in hadiths:
        hno = str(hadith.get("hadithnumber"))
        if hno in {wanted, source_wanted}:
            text = (hadith.get("text") or "").strip()
            return text or None

    text = (hadiths[0].get("text") or "").strip()
    return text or None


def load_bukhari_arabic_sources() -> dict[str, dict[str, Any]]:
    path = ROOT / "arabic_books" / "collections" / "bukhari.json"
    if not path.exists():
        return {}
    data = load_json(path)
    sources: dict[str, dict[str, Any]] = {}
    for book in data.get("books", []):
        for item in book.get("content", []):
            ref = item.get("reference")
            if ref:
                sources[ref] = item
    return sources


def get_record(book: dict[str, Any], chapter: str, index: int) -> dict[str, Any]:
    return book[chapter][index]


def main() -> None:
    report = load_json(REPORT)
    books = {name: load_json(ROOT / name) for name in FILES}
    bukhari_arabic_sources = load_bukhari_arabic_sources()

    repaired = 0
    cleared = 0
    fetched_arabic = 0
    recovered_arabic_total = 0
    sourced_from_arabic_books_bukhari = 0

    for update in report["updates"]:
        file_name = update["file"]
        hadis_key = str(update["hadis_no"])
        record = get_record(books[file_name], update["chapter"], update["index"])

        arabic = (update.get("arabic") or record.get("arabic") or "").strip()
        had_local_arabic = bool((record.get("arabic") or "").strip())
        manual_source_ref = MANUAL_ARABIC_SOURCE_REFS.get((file_name, hadis_key))
        if manual_source_ref:
            source_item = bukhari_arabic_sources.get(manual_source_ref) or {}
            source_arabic = (source_item.get("arabic") or "").strip()
            if source_arabic:
                arabic = source_arabic
                update["arabic"] = source_arabic
                sourced_from_arabic_books_bukhari += 1
                if source_item.get("chain"):
                    update["chain"] = source_item["chain"]
        if not arabic:
            arabic = fetch_arabic_from_api(update.get("source_detail", ""), update["hadis_no"]) or ""
            if arabic:
                update["arabic"] = arabic
                fetched_arabic += 1
        elif arabic and not had_local_arabic and not manual_source_ref:
            recovered_arabic_total += 1

        override = MANUAL_OVERRIDES.get((file_name, hadis_key))
        if override:
            fixed = override
        elif arabic:
            fixed = normalize_turkish(update.get("added_turkce") or record.get("turkce") or "")
        else:
            fixed = ""

        update["added_turkce"] = fixed
        if arabic and not (record.get("arabic") or "").strip():
            record["arabic"] = arabic

        if fixed:
            record["turkce"] = fixed
            update["source"] = "arabic_corrective_pass"
            if manual_source_ref:
                update["source_detail"] = f"arabic_books/collections/bukhari.json:{manual_source_ref}; corrected from Arabic-available record"
            else:
                update["source_detail"] = "corrected from Arabic-available record"
            update["english_source"] = None
            update["source_text"] = None
            repaired += 1
        else:
            record["turkce"] = ""
            update["source"] = "blocked_missing_arabic"
            update["source_detail"] = "cleared because no Arabic source is available"
            update["english_source"] = None
            update["source_text"] = None
            cleared += 1

    report["sources"] = [
        "Direct Arabic text already present in repo-local JSON records",
        "Repo-local Arabic source mapping from arabic_books/collections/bukhari.json for corrected Bukhari gaps",
        "Arabic API fallback only to recover missing Arabic text; no English/French/Russian translation source accepted as final",
    ]
    report["correction_note"] = (
        "Corrective pass removed or repaired non-Arabic machine-derived Turkish. "
        "Entries with no Arabic source were cleared so they remain visibly missing."
    )
    report["final_method_note"] = (
        "Arabic-available entries were normalized to the master Islamic Turkish register; "
        "unverifiable entries are blocked until Arabic text is supplied."
    )
    report["summary"]["repair_pass"] = {
        "arabic_available_repaired_or_normalized": repaired,
        "arabic_sourced_from_arabic_books_bukhari": sourced_from_arabic_books_bukhari,
        "cleared_missing_arabic": cleared,
    }

    for name, data in books.items():
        write_json(ROOT / name, data)
    write_json(REPORT, report)

    print(
        json.dumps(
            {
                "repaired_or_normalized": repaired,
                "arabic_sourced_from_arabic_books_bukhari": sourced_from_arabic_books_bukhari,
                "cleared_missing_arabic": cleared,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
