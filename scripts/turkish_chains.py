#!/usr/bin/env python3
"""Convert JSON hadith chain fields to Turkish-style narrator names.

Usage:
  python3 scripts/turkish_chains.py --dry-run
  python3 scripts/turkish_chains.py
  python3 scripts/turkish_chains.py buhari.json muslim.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARABIC_RE = re.compile(r"[\u0621-\u064a\u066e-\u06d3]")
ARABIC_WORD_RE = re.compile(r"[\u0600-\u06ff]+|[^\u0600-\u06ff]+")
DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")


CHAR_MAP = str.maketrans(
    {
        "ʿ": "",
        "ʾ": "",
        "‘": "",
        "’": "",
        "`": "",
        "´": "",
        "Ā": "Â",
        "ā": "â",
        "Á": "Â",
        "á": "â",
        "Ī": "Î",
        "ī": "î",
        "Ū": "Û",
        "ū": "û",
        "Ḥ": "H",
        "ḥ": "h",
        "Ṣ": "S",
        "ṣ": "s",
        "Ṭ": "T",
        "ṭ": "t",
        "Ḍ": "D",
        "ḍ": "d",
        "Ẓ": "Z",
        "ẓ": "z",
        "Ṯ": "S",
        "ṯ": "s",
        "Ḏ": "Z",
        "ḏ": "z",
        "Ḳ": "K",
        "ḳ": "k",
    }
)

PRE_REPLACEMENTS = [
    ("ʿAbd Allāh", "Abdullah"),
    ("ʿAbdullāh", "Abdullah"),
    ("Abd Allāh", "Abdullah"),
    ("Abū", "Ebû"),
    ("ʾAbū", "Ebû"),
    ("Umm ", "Ümm "),
    ("[Chain ", "[Zincir "),
    (" And ", " ve "),
    (" and ", " ve "),
    (" from my father", " babamdan"),
    (" from his father", " babasından"),
    (" from her father", " babasından"),
    (" from my mother", " annemden"),
    (" from his mother", " annesinden"),
    (" from her mother", " annesinden"),
    (" from my moser", " annemden"),
    (" from his moser", " annesinden"),
    (" from her moser", " annesinden"),
    (" from his aunt", " teyzesinden"),
    (" from her aunt", " teyzesinden"),
    (" from his uncle", " amcasından"),
    (" from her uncle", " amcasından"),
    (" from my grandfather", " dedemden"),
    (" from his grandfather", " dedesinden"),
    (" from my cousin", " kuzenimden"),
    (" from his cousin", " kuzeninden"),
    (" a freed slave of ", " azatlısı "),
    (" a man from ", " bir adam / "),
    (" a neighboriyah from ", " bir kadın / "),
    ("Hadhā Ḥadīthuh", "bu onun hadisi"),
    ("Samiʿtuh", "onu işittim"),
    ("Saʾalt", "sordum"),
]

PHRASE_REPLACEMENTS = [
    (r"\bAbd Allah\b", "Abdullah"),
    (r"\bAbd (?:al|el)-Rahman\b", "Abdurrahman"),
    (r"\bAbd (?:al|el)-Rahmân\b", "Abdurrahman"),
    (r"\bAbd er-Rahman\b", "Abdurrahman"),
    (r"\bAbd (?:al|el)-Malik\b", "Abdülmelik"),
    (r"\bAbd (?:al|el)-Azîz\b", "Abdülazîz"),
    (r"\bAbd (?:al|el)-Wâhid\b", "Abdülvâhid"),
]

DIGRAPH_REPLACEMENTS = [
    ("Kh", "H"),
    ("kh", "h"),
    ("Sh", "Ş"),
    ("sh", "ş"),
    ("Dh", "Z"),
    ("dh", "z"),
    ("Th", "S"),
    ("th", "s"),
    ("J", "C"),
    ("j", "c"),
    ("Q", "K"),
    ("q", "k"),
    ("W", "V"),
    ("w", "v"),
]

WORD_MAP = {
    "Abdullah": "Abdullah",
    "Ubaydullah": "Ubeydullah",
    "Ubaydullâh": "Ubeydullah",
    "Muhammad": "Muhammed",
    "Ahmad": "Ahmed",
    "Ibrâhîm": "İbrahim",
    "Ibrahim": "İbrahim",
    "Ismâîl": "İsmail",
    "Ishâk": "İshâk",
    "Ishâq": "İshâk",
    "İşâk": "İshâk",
    "Yahyâ": "Yahyâ",
    "Yamar": "Ya'mer",
    "Yûnus": "Yûnus",
    "Yûsuf": "Yûsuf",
    "Mûsâ": "Mûsâ",
    "Mâlik": "Mâlik",
    "Sufyân": "Süfyân",
    "Umar": "Ömer",
    "Uthmân": "Osman",
    "Usmân": "Osman",
    "Alî": "Ali",
    "Âishah": "Âişe",
    "Âişah": "Âişe",
    "Aishah": "Âişe",
    "Fâtimah": "Fâtıma",
    "Hafşah": "Hafsa",
    "Safiyyah": "Safiyye",
    "Maymûnah": "Meymûne",
    "Hurayrah": "Hureyre",
    "Jâbir": "Câbir",
    "Jabir": "Câbir",
    "Anas": "Enes",
    "Zubayr": "Zübeyr",
    "Zuhayr": "Züheyr",
    "Zuhrî": "Zührî",
    "Zuhri": "Zührî",
    "Salamah": "Seleme",
    "Kâsim": "Kâsım",
    "Kasim": "Kâsım",
    "Kutaybah": "Kuteybe",
    "Hishâm": "Hişâm",
    "Hisham": "Hişâm",
    "Urwah": "Urve",
    "Urvah": "Urve",
    "Layth": "Leys",
    "Lays": "Leys",
    "Laysî": "Leysî",
    "Awzâî": "Evzâî",
    "Katâdah": "Katâde",
    "Katadah": "Katâde",
    "Shubah": "Şube",
    "Shuayb": "Şuayb",
    "Shaybah": "Şeybe",
    "Shihâb": "Şihâb",
    "Bashîr": "Beşîr",
    "Bishr": "Bişr",
    "Cafar": "Cafer",
    "Cubayr": "Cübeyr",
    "Curayc": "Cüreyc",
    "Hâlid": "Hâlid",
    "Halid": "Hâlid",
    "Hattâb": "Hattâb",
    "Sâbit": "Sâbit",
    "Hârith": "Hâris",
    "Haris": "Hâris",
    "Muâdh": "Muâz",
    "Muaz": "Muâz",
    "Yazîd": "Yezîd",
    "Yazid": "Yezîd",
    "Vahb": "Vehb",
    "Vakî": "Vekî",
    "Dâvûd": "Dâvûd",
    "Davûd": "Dâvûd",
    "Bakr": "Bekir",
    "Saîd": "Saîd",
    "Said": "Saîd",
    "Masûd": "Mesûd",
    "Masud": "Mesûd",
    "Ansârî": "Ensârî",
    "Kuraşî": "Kureyşî",
    "Kurayshî": "Kureyşî",
    "Makkî": "Mekkî",
    "Madanî": "Medenî",
    "Taymî": "Teymî",
    "Laythî": "Leysî",
    "Anbarî": "Anberî",
    "Hamdânî": "Hemdânî",
    "Humaydî": "Humeydî",
    "Alkamah": "Alkame",
    "Maslamah": "Mesleme",
    "Kanab": "Ka'nab",
    "Umayr": "Umeyr",
    "Ukayl": "Ukayl",
    "Bukayr": "Bükeyr",
    "Huzaymah": "Huzeyme",
    "Haysamah": "Hayseme",
    "Hanzalah": "Hanzale",
    "Ikrimah": "İkrime",
    "Buraydah": "Büreyde",
    "Mamar": "Ma'mer",
}

AR_WORD_MAP = {
    "الله": "Allah",
    "عبد": "Abd",
    "عبدالله": "Abdullah",
    "الرحمن": "er-Rahman",
    "مالك": "Mâlik",
    "محمد": "Muhammed",
    "احمد": "Ahmed",
    "ابراهيم": "İbrahim",
    "اسحاق": "İshâk",
    "يحيى": "Yahyâ",
    "يونس": "Yûnus",
    "يوسف": "Yûsuf",
    "موسى": "Mûsâ",
    "نافع": "Nâfi",
    "ابن": "İbn",
    "ابي": "Ebû",
    "ابا": "Ebû",
    "ابو": "Ebû",
    "ابيه": "babasından",
    "ام": "Ümm",
    "امير": "emîr",
    "محمد": "Muhammed",
    "المنكدر": "el-Münkedir",
    "صفوان": "Safvân",
    "سليم": "Süleym",
    "سلمه": "Seleme",
    "الحارث": "el-Hâris",
    "التيمي": "et-Teymî",
    "ربيعة": "Rabîa",
    "ربيعه": "Rabîa",
    "الهدير": "el-Hüdeyr",
    "دينار": "Dînâr",
    "العلاء": "el-Alâ",
    "يعقوب": "Yakûb",
    "هريرة": "Hureyre",
    "هريره": "Hureyre",
    "شهاب": "Şihâb",
    "سعيد": "Saîd",
    "المسيب": "el-Müseyyeb",
    "هشام": "Hişâm",
    "عروة": "Urve",
    "عروه": "Urve",
    "بكر": "Bekir",
    "عمرة": "Amre",
    "عمره": "Amre",
    "عائشة": "Âişe",
    "عايشه": "Âişe",
    "عمر": "Ömer",
    "الخطاب": "el-Hattâb",
    "طلحة": "Talha",
    "طلحه": "Talha",
    "اسلم": "Eslem",
    "واقد": "Vâkid",
    "الجحفة": "el-Cuhfe",
    "الجحفه": "el-Cuhfe",
    "حميد": "Humeyd",
    "قيس": "Kays",
    "ثور": "Sevr",
    "زيد": "Zeyd",
    "الديلي": "ed-Dîlî",
    "ثابت": "Sâbit",
    "عبيد": "Ubeyd",
    "النعمان": "en-Numân",
    "بشير": "Beşîr",
    "العباس": "Abbâs",
    "عباس": "Abbâs",
    "مسعود": "Mesûd",
    "خالد": "Hâlid",
    "الجهني": "el-Cühenî",
    "الزبير": "ez-Zübeyr",
    "عتبة": "Utbe",
    "عتبه": "Utbe",
    "العزيز": "el-Azîz",
    "صفية": "Safiyye",
    "صفيه": "Safiyye",
    "سليمان": "Süleymân",
    "يسار": "Yesâr",
    "صدقة": "Sadaka",
    "نوفل": "Nevfel",
    "المطلب": "el-Muttalib",
}

AR_SKIP_WORDS = {
    "وحدثني",
    "وحدثنيه",
    "حدثني",
    "حدثنا",
    "واخبرنا",
    "اخبرنا",
    "اخبراه",
    "اخبرته",
    "حدثه",
    "يحدث",
    "انه",
    "انها",
    "انهما",
    "ان",
    "قال",
    "فقال",
    "قالوا",
    "يقول",
    "تقول",
    "سمع",
    "سمعت",
    "سمعا",
    "بلغهم",
    "بلغه",
    "ما",
}

AR_CONNECTORS = {"عن", "عني"}
AR_BIN_WORDS = {"بن", "بني", "بنا"}
AR_BINT_WORDS = {"بنت"}

AR_FALLBACK = {
    "ا": "a",
    "أ": "a",
    "إ": "i",
    "آ": "â",
    "ب": "b",
    "ت": "t",
    "ث": "s",
    "ج": "c",
    "ح": "h",
    "خ": "h",
    "د": "d",
    "ذ": "z",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "ş",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "z",
    "ع": "",
    "غ": "g",
    "ف": "f",
    "ق": "k",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "ة": "e",
    "و": "v",
    "ؤ": "v",
    "ي": "y",
    "ى": "â",
    "ئ": "y",
    "ء": "",
}


def normalize_arabic_word(word: str) -> str:
    word = DIACRITICS_RE.sub("", word)
    word = word.replace("ـ", "")
    word = word.strip("،؛:.()[]{}")
    if len(word) > 1 and word[0] in {"و", "ف"}:
        word = word[1:]
    word = word.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ؤ": "و", "ئ": "ي", "ة": "ه"}))
    return word


def transliterate_arabic_word(word: str) -> str:
    normalized = normalize_arabic_word(word)
    if normalized in AR_WORD_MAP:
        return AR_WORD_MAP[normalized]
    return "".join(AR_FALLBACK.get(ch, ch) for ch in normalized)


def arabic_chain_to_latin(chain: str) -> str:
    parts: list[str] = []
    for token in ARABIC_WORD_RE.findall(chain):
        if not ARABIC_RE.search(token):
            parts.append(token)
            continue

        normalized = normalize_arabic_word(token)
        if not normalized:
            parts.append(token)
            continue
        had_prefix = len(normalized) > 1 and DIACRITICS_RE.sub("", token).replace("ـ", "")[0] in {"و", "ف"}

        if normalized in AR_CONNECTORS:
            parts.append(" > ")
        elif normalized in AR_BIN_WORDS:
            parts.append(" b. ")
        elif normalized in AR_BINT_WORDS:
            parts.append(" bint ")
        elif normalized in AR_SKIP_WORDS:
            continue
        else:
            if had_prefix and normalized not in {"الله"}:
                parts.append(" ve ")
            parts.append(transliterate_arabic_word(token))

    text = "".join(parts)
    text = re.sub(r"\s*>\s*", " > ", text)
    text = re.sub(r"(?:\s*>\s*){2,}", " > ", text)
    text = re.sub(r"\s+", " ", text).strip(" >")
    return text


def apply_word_map(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return WORD_MAP.get(match.group(0), match.group(0))

    return re.sub(r"[A-Za-zÂâÎîÛûÖöÜüİıŞşÇçĞğ']+", replace, text)


def latin_chain_to_turkish(chain: str) -> str:
    text = chain
    for source, target in PRE_REPLACEMENTS:
        text = text.replace(source, target)

    text = re.sub(r"\bAnd\b", "ve", text)
    text = re.sub(r"\band\b", "ve", text)
    text = re.sub(r"\bChain\b", "Zincir", text)
    text = re.sub(r"\bfrom\b", "den", text)
    text = re.sub(r"\ba man\b", "bir adam", text)
    text = re.sub(r"\bWa(?=[A-ZÂÎÛÖÜİŞÇ])", "ve ", text)

    text = text.translate(CHAR_MAP)
    text = re.sub(r"\bal-", "el-", text)
    text = re.sub(r"\bAl-", "El-", text)
    text = re.sub(r"\bVa(?=[A-ZÂÎÛÖÜİŞÇYAEI])", "ve ", text)
    text = re.sub(r"\bVa(?=(?:yûnus|abî|akî|mughîrah|wakî|saîd))", "ve ", text, flags=re.IGNORECASE)

    for pattern, replacement in PHRASE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)

    for source, target in DIGRAPH_REPLACEMENTS:
        text = text.replace(source, target)

    for _ in range(2):
        text = apply_word_map(text)

    text = re.sub(r"\bIbn\b", "İbn", text)
    text = re.sub(r"\sibn\b", " ibn", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def turkish_chain(chain: str) -> str:
    if ARABIC_RE.search(chain):
        chain = arabic_chain_to_latin(chain)
    return latin_chain_to_turkish(chain)


def update_chains(value: Any) -> tuple[Any, int]:
    changed = 0
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if key == "chain" and isinstance(child, str):
                converted = turkish_chain(child)
                result[key] = converted
                changed += converted != child
            else:
                result[key], child_changed = update_chains(child)
                changed += child_changed
        return result, changed

    if isinstance(value, list):
        result = []
        for child in value:
            converted_child, child_changed = update_chains(child)
            result.append(converted_child)
            changed += child_changed
        return result, changed

    return value, changed


def json_files(paths: list[str]) -> list[Path]:
    if paths:
        return [Path(path) for path in paths]
    return sorted(ROOT.glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="JSON files to update. Defaults to all root *.json files.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    args = parser.parse_args()

    total_changed = 0
    for path in json_files(args.files):
        full_path = path if path.is_absolute() else ROOT / path
        data = json.loads(full_path.read_text(encoding="utf-8"))
        updated, changed = update_chains(data)
        total_changed += changed

        if args.dry_run:
            print(f"{path}: {changed} chain value(s) would change")
            continue

        if changed:
            full_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{path}: {changed} chain value(s) changed")

    print(f"total: {total_changed} chain value(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
