import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codebase"))
import ai


class ModelProviderTests(unittest.TestCase):
    def test_requests_use_provider_specific_settings(self):
        response = {
            "model": "example",
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5},
        }
        schema = {"name": "example", "schema": {"type": "object"}}
        for provider in ("openai", "openrouter"):
            with self.subTest(provider=provider), \
                 patch.object(ai, "MODEL_PROVIDER", provider), \
                 patch.object(ai, "MODEL_NAME", "example"), \
                 patch.object(ai, "API_KEY", "test-key"), \
                 patch("urllib.request.urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
                result = ai.call_model("system", "user", schema=schema)
                request = urlopen.call_args.args[0]
                body = json.loads(request.data)
                self.assertEqual(request.full_url, ai.API_URLS[provider])
                self.assertEqual(body["response_format"]["json_schema"]["name"], "example")
                self.assertEqual("provider" in body, provider == "openrouter")
                self.assertEqual("reasoning" in body, provider == "openrouter")
                self.assertEqual((result["tokens_in"], result["tokens_out"]), (12, 5))

    def test_openai_missing_key_fails_explicitly(self):
        with patch.object(ai, "MODEL_PROVIDER", "openai"), patch.object(ai, "API_KEY", ""):
            with self.assertRaisesRegex(ai.ModelError, "OPENAI_API_KEY"):
                ai.call_model("system", "user")


if __name__ == "__main__":
    unittest.main()
