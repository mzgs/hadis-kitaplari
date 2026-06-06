import json
import tempfile
import unittest
from pathlib import Path

from translate_chatgpt_web import write_response


class WriteResponseTests(unittest.TestCase):
    def write_and_load(self, body, expected_reference=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "translation.json"
            write_response(body, output_path, expected_reference)
            return json.loads(output_path.read_text(encoding="utf-8"))

    def test_writes_valid_translation_response(self):
        body = json.dumps(
            {
                "response": json.dumps(
                    {
                        "tr": "Türkçe metin",
                        "reference": "Sahih al-Bukhari 1",
                        "grade": "",
                    },
                    ensure_ascii=False,
                )
            },
            ensure_ascii=False,
        )

        self.assertEqual(
            self.write_and_load(body, "Sahih al-Bukhari 1"),
            {
                "tr": "Türkçe metin",
                "reference": "Sahih al-Bukhari 1",
                "grade": "",
            },
        )

    def test_repairs_unescaped_quotes_in_translation(self):
        body = json.dumps(
            {
                "response": (
                    '{"tr":"Resûlullah (s.a.v.) buyurdu: "Oku!"",'
                    '"reference":"Sahih al-Bukhari 3","grade":""}'
                )
            },
            ensure_ascii=False,
        )

        result = self.write_and_load(body, "Sahih al-Bukhari 3")

        self.assertEqual(result["reference"], "Sahih al-Bukhari 3")
        self.assertIn("Oku!", result["tr"])

    def test_recovers_long_translation_split_into_extra_repaired_fields(self):
        body = (
            '{"tr":"Başlangıçta "ilk söz" söylendi. Sonra ona "ikinci söz" '
            'denildi.","reference":"Sahih al-Bukhari 7","grade":""}'
        )

        result = self.write_and_load(body, "Sahih al-Bukhari 7")

        self.assertEqual(
            result["tr"],
            'Başlangıçta "ilk söz" söylendi. Sonra ona "ikinci söz" denildi.',
        )

    def test_rejects_wrong_reference(self):
        body = json.dumps(
            {
                "response": {
                    "tr": "Türkçe metin",
                    "reference": "Sahih al-Bukhari 2",
                    "grade": "",
                }
            },
            ensure_ascii=False,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "reference"):
                write_response(
                    body,
                    Path(temp_dir) / "translation.json",
                    "Sahih al-Bukhari 1",
                )

    def test_rejects_missing_or_extra_fields(self):
        body = '{"tr":"Türkçe metin","reference":"Ref","unexpected":"value"}'

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "exactly"):
                write_response(body, Path(temp_dir) / "translation.json")


if __name__ == "__main__":
    unittest.main()
