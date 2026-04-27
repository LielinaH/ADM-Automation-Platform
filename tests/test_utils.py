import unittest

from adm_pipeline.utils import parse_json_response_text


class UtilsTests(unittest.TestCase):
    def test_parse_json_response_text_allows_trailing_text(self) -> None:
        payload = parse_json_response_text('{"ok": true, "value": 1}\nExtra explanation')
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["value"], 1)

    def test_parse_json_response_text_allows_code_fences(self) -> None:
        payload = parse_json_response_text("```json\n{\"ok\": true}\n```\nnotes")
        self.assertEqual(payload["ok"], True)


if __name__ == "__main__":
    unittest.main()
