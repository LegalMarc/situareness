import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/situareness-sources/scripts/validate_catalog.py"
spec = importlib.util.spec_from_file_location("catalog", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "config/source-catalog.example.json").read_text())

    def test_example_and_cli(self):
        catalog.validate(self.data)
        run = subprocess.run([sys.executable, str(SCRIPT), str(ROOT / "config/source-catalog.example.json")], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_invalid_fields_and_references(self):
        variants = []
        data = copy.deepcopy(self.data); data["locations"][0]["address"] = "private"; variants.append(data)
        data = copy.deepcopy(self.data); data["sources"][0]["location_ids"] = ["missing"]; variants.append(data)
        data = copy.deepcopy(self.data); data["locations"].append(copy.deepcopy(data["locations"][0])); variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                catalog.validate(data)

    def test_invalid_urls(self):
        for value in ("http://example.com", "https://u:p@example.com", "https://example.com:99999", "https://example.com/has space", "https://example.com/?API_KEY=redacted", "https://example.com/?%74oken=redacted"):
            self.data["sources"][0]["channel_url"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                catalog.validate(self.data)

    def test_proposal_and_unverified_cannot_be_enabled(self):
        src = self.data["sources"][0]
        src["enabled"] = True
        src["access_status"] = "unverified"
        with self.assertRaises(ValueError): catalog.validate(self.data)
        src.update(access_status="public_api/feed", checked_at="2026-11-16", evidence_urls=["https://example.org/evidence"], runtime_support="proposed")
        with self.assertRaises(ValueError): catalog.validate(self.data)
        src["runtime_support"] = "supported"
        catalog.validate(self.data)

    def test_bad_dates_and_intervals(self):
        src = self.data["sources"][0]
        src["checked_at"] = "2026-02-30"
        with self.assertRaises(ValueError): catalog.validate(self.data)
        src["checked_at"] = None
        for value in (0, -1, True, 1.5):
            src["poll_interval_seconds"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): catalog.validate(self.data)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"x": 1, "x": 2}', object_pairs_hook=catalog.unique_object)


if __name__ == "__main__":
    unittest.main()
