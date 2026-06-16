# DOC to Hadith JSON Workflow

Use this guide when converting a Word `.doc` / `.docx` hadith book in this folder into the repository's fixed JSON format.

## Output File

Create the JSON next to the source document:

```text
fromdoc/<source-file-name-without-extension>.json
```

Example:

```text
fromdoc/tk_Riad_righteous.doc
fromdoc/tk_Riad_righteous.json
```

## Fixed JSON Format

The output format is fixed. Do not add `english`.

```json
{
  "collection": "Collection Name",
  "books": [
    {
      "book_name": "Book or Chapter Name",
      "content": [
        {
          "reference": "Collection Name 1",
          "arabic": "Arabic hadith text",
          "turkish": "Turkish translation text"
        }
      ]
    }
  ]
}
```

Required rules:

- Top-level keys: `collection`, `books`.
- Each book must have `book_name` and `content`.
- Each hadith must have `reference`, `arabic`, and `turkish`.
- `turkish` key must always exist.
- `arabic` key must always exist.
- Do not include `english`.
- Keep references sequential in document order unless the source has a reliable official numbering system that must be preserved.

## Workflow

1. Inspect the document type.

```bash
file fromdoc/<file>.doc
```

2. Convert Word content to text.

For old `.doc` files on macOS:

```bash
textutil -convert txt -output /tmp/<file>.txt fromdoc/<file>.doc
```

For `.docx` files:

```bash
textutil -convert txt -output /tmp/<file>.txt fromdoc/<file>.docx
```

3. Inspect the text before parsing.

```bash
sed -n '1,160p' /tmp/<file>.txt
rg -n 'BÖLÜM|^[[:space:]]*[0-9]+[-:]|^[[:space:]]*[0-9]+[[:space:]]' /tmp/<file>.txt | sed -n '1,120p'
rg -n 'BÖLÜM|^[[:space:]]*[0-9]+[-:]|^[[:space:]]*[0-9]+[[:space:]]' /tmp/<file>.txt | tail -120
```

4. Identify the source structure.

Look for:

- Collection title.
- Chapter or book heading markers.
- Hadith start markers.
- Arabic text start markers.
- Turkish translation start markers.
- Cases where Arabic and Turkish appear on the same line.
- Bad source numbering, repeated references, missing colons, or OCR-like line damage.

The document format may differ from book to book, so adapt the parser to the observed markers instead of assuming one layout.

5. Generate JSON.

Use a script or one-off parser that:

- Reads the converted text.
- Splits the content into books/chapters.
- Splits each book into hadith entries.
- Writes only `reference`, `arabic`, and `turkish` for each hadith.
- Writes UTF-8 JSON with `ensure_ascii=False`.

Recommended JSON write pattern:

```python
import json
from pathlib import Path

data = {
    "collection": "Collection Name",
    "books": books,
}

Path("fromdoc/<file>.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
```

## Validation

Run these checks before considering the job done:

```bash
python3 -m json.tool fromdoc/<file>.json >/tmp/jsoncheck.out
```

```bash
python3 - <<'PY'
import json
import re
from pathlib import Path

p = Path("fromdoc/<file>.json")
data = json.loads(p.read_text(encoding="utf-8"))
items = [h for b in data["books"] for h in b["content"]]

print("collection", data.get("collection"))
print("books", len(data.get("books", [])))
print("hadiths", len(items))
print("english_keys", sum("english" in h for h in items))
print("missing_reference", sum("reference" not in h for h in items))
print("missing_arabic", sum("arabic" not in h for h in items))
print("missing_turkish", sum("turkish" not in h for h in items))
print("empty_arabic", sum(not h.get("arabic") for h in items))
print("empty_turkish", sum(not h.get("turkish") for h in items))

refs = []
for h in items:
    m = re.search(r"(\\d+)$", h.get("reference", ""))
    refs.append(int(m.group(1)) if m else None)

if all(isinstance(x, int) for x in refs):
    print("refs_sequential", refs == list(range(1, len(refs) + 1)))
PY
```

Expected:

- `english_keys 0`
- `missing_reference 0`
- `missing_arabic 0`
- `missing_turkish 0`
- `empty_arabic 0`
- `empty_turkish 0`

If `refs_sequential` is `False`, inspect whether the source has intentional numbering or parser mistakes.

## Parser Notes

Common issues to handle:

- Old `.doc` files can contain form-feed page breaks.
- Arabic and Turkish may appear on the same extracted line.
- Some hadith numbers may be malformed, such as `-11عن`, `186 عَنْ`, or `1990-` followed by `1890:`.
- Some chapters may use `BÖLÜM: 1`, while others may use `BÖLÜM 1`.
- The same hadith may be repeated later as a cross-reference. Preserve it if the document presents it as content.
- Ignore isolated page numbers or footnote markers.
- Do not silently keep entries with empty `arabic` or empty `turkish`; fix the parser or inspect the source manually.

## Final Checklist

- JSON is in the same folder as the source document.
- File is valid UTF-8 JSON.
- Top-level format matches the fixed schema.
- No `english` fields exist.
- Every hadith has `reference`, `arabic`, and `turkish`.
- Chapter count and hadith count are plausible compared with source markers.
- First and last entries were manually spot-checked against the converted text.
