"""Exercise release packaging in isolated directories, never the real dist directory."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]


class PackageTest(unittest.TestCase):
    def test_reproducibility_safety_and_required_files(self):
        (ROOT / "work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            for name in (
                "extension",
                "custom_components/situareness",
                "home-assistant",
                "docs/ha",
            ):
                shutil.copytree(
                    ROOT / name,
                    source / name,
                    ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
                )
            (source / "tools").mkdir()
            for name in ("package.py",):
                shutil.copy2(ROOT / "tools" / name, source / "tools" / name)
            shutil.copy2(
                ROOT / "docs/extension-quickstart.md",
                source / "docs/extension-quickstart.md",
            )
            shutil.copy2(ROOT / "package.json", source / "package.json")
            # An installed private file must never enter either archive.
            (source / "home-assistant/situareness.json").write_text(
                '{"private":"secret"}'
            )
            script = source / "tools/package.py"
            for name in ("one", "two"):
                subprocess.run(
                    [sys.executable, str(script), "--output-dir", str(base / name)],
                    check=True,
                    capture_output=True,
                )
            for one in (base / "one").iterdir():
                self.assertEqual(
                    one.read_bytes(), (base / "two" / one.name).read_bytes()
                )
                if one.suffix == ".zip":
                    with zipfile.ZipFile(one) as archive:
                        names = archive.namelist()
                        self.assertIn("README.md", names)
                        self.assertNotIn("home-assistant/situareness.json", names)
                        if "home-assistant" in one.name:
                            self.assertIn(
                                "home-assistant/situareness.example.json", names
                            )
            example = source / "home-assistant/situareness.example.json"
            value = json.loads(example.read_text())
            self.assertEqual(
                set(value["locations"]), {"nyc_sample", "washington_dc_sample"}
            )
            value["live_enabled"] = True
            example.write_text(json.dumps(value))
            result = subprocess.run(
                [sys.executable, str(script), "--output-dir", str(base / "unsafe")],
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            value["live_enabled"] = False
            example.write_text(json.dumps(value))
            manifest = source / "extension/manifest.json"
            value = json.loads(manifest.read_text())
            value["version"] = "99.0.0"
            manifest.write_text(json.dumps(value))
            result = subprocess.run(
                [sys.executable, str(script), "--output-dir", str(base / "mismatch")],
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
