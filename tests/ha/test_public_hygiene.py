"""Unit tests for tools/check_public_hygiene.py."""

from __future__ import annotations

import hashlib
import importlib.util
import io
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def _load_hygiene_module():
    module_path = ROOT / "tools/check_public_hygiene.py"
    spec = importlib.util.spec_from_file_location("check_public_hygiene", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hygiene = _load_hygiene_module()


def _init_git_repo(repo_dir: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "ci@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "CI Fixture"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_add_all(repo_dir: Path, force: bool = False) -> None:
    cmd = ["git", "add"]
    if force:
        cmd.append("-f")
    cmd.append(".")
    subprocess.run(cmd, cwd=repo_dir, check=True, capture_output=True, text=True)


def _write_deterministic_package_script(repo_dir: Path, zip_builder_body: str) -> None:
    tools_dir = repo_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    script = tools_dir / "package.py"
    script.write_text(
        zip_builder_body,
        encoding="utf-8",
    )


class PublicHygieneTest(unittest.TestCase):
    def test_repo_passes_all_public_hygiene_checks(self):
        errors = hygiene.run_all_checks(ROOT)
        self.assertEqual(errors, [])

        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout, stderr
            rc = hygiene.main(["--root", str(ROOT)])
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
        self.assertEqual(rc, 0, stderr.getvalue())
        self.assertIn("Public hygiene passed:", stdout.getvalue())

    def test_forbidden_paths_detected_and_allowed_examples_permitted(self):
        forbidden = [
            "ignored-resources/private-config/room.json",
            "work/tmp.txt",
            "dist/bundle.zip",
            ".venv/lib/python.py",
            "node_modules/pkg/index.js",
            ".env",
            ".env.local",
            "settings.local.json",
            "events.sqlite",
            "events.sqlite3-wal",
            "cache.db",
            "cache.db-shm",
            "home-assistant/situareness.json",
            "nested/.DS_Store",
            "playwright-report/index.html",
            "test-results/trace.zip",
        ]
        errors = hygiene.check_forbidden_tracked_paths(forbidden)
        self.assertEqual(len(errors), len(forbidden))

        allowed = [
            ".env.example",
            "home-assistant/situareness.example.json",
            "config/watch-configuration.json",
            "tools/check_public_hygiene.py",
        ]
        self.assertEqual(hygiene.check_forbidden_tracked_paths(allowed), [])

    def test_temp_git_repo_rejects_forbidden_tracked_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / "ignored-resources").mkdir()
            (repo / "ignored-resources/secret.json").write_text(
                "{}\n", encoding="utf-8"
            )
            (repo / "docs").mkdir()
            (repo / "docs/INDEX.md").write_text(
                "## docs/\n- `docs/INDEX.md` — Index.\n", encoding="utf-8"
            )
            _git_add_all(repo, force=True)
            tracked = hygiene.git_tracked_files(repo)
            errors = hygiene.check_forbidden_tracked_paths(tracked)
            self.assertTrue(
                any("ignored-resources/secret.json" in err for err in errors),
                errors,
            )

    def test_secret_scanner_detects_private_key_tokens_and_skips_binary_and_placeholders(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            pem_prefix = "-----BEGIN "
            pem_suffix = "RSA PRIVATE KEY-----"
            pem_header = pem_prefix + pem_suffix
            ghp_token = "ghp_" + "AbCdEf0123456789GhIjKlMn"
            gh_pat = "github_pat_" + "AbCdEf0123456789_" * 2
            aws_key = "AKIA" + "0123456789ABCDEF"
            bearer_real = "Bearer " + "eyJhbGciOiJIUzI1NiJ9.payloadvalue"

            (repo / "leak.txt").write_text(
                "\n".join([pem_header, ghp_token, gh_pat, aws_key, bearer_real]) + "\n",
                encoding="utf-8",
            )
            (repo / "docs.md").write_text(
                "Authorization: Bearer <token>\n"
                "Authorization: Bearer your-token-placeholder-value\n"
                "Authorization: Bearer example-token-not-secret\n",
                encoding="utf-8",
            )
            (repo / "binary.bin").write_bytes(
                b"\x00\x01" + pem_header.encode("utf-8") + b"\xff\xfe"
            )
            (repo / "nonutf8.dat").write_bytes(b"\xff\xfe\xfd" + ghp_token.encode())

            findings = hygiene.check_tracked_secrets(
                repo, ["leak.txt", "docs.md", "binary.bin", "nonutf8.dat"]
            )
            self.assertEqual(len(findings), 5, findings)
            self.assertTrue(any("private key header" in f for f in findings))
            self.assertTrue(any("GitHub classic token" in f for f in findings))
            self.assertTrue(any("GitHub fine-grained token" in f for f in findings))
            self.assertTrue(any("AWS access key ID" in f for f in findings))
            self.assertTrue(any("Bearer token" in f for f in findings))
            for finding in findings:
                self.assertNotIn(ghp_token, finding)
                self.assertNotIn(aws_key, finding)

    def test_non_deterministic_packaging_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _write_deterministic_package_script(
                repo,
                """
import argparse, hashlib, json, zipfile
from pathlib import Path
import time

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
zip_path = args.output_dir / "bundle.zip"
with zipfile.ZipFile(zip_path, "w") as zf:
    zf.writestr("hello.txt", f"nonce-{time.time_ns()}")
sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
(args.output_dir / "manifest.json").write_text(
    json.dumps({"version": "0.1.0", "bundles": [{"name": "bundle.zip", "sha256": sha}]}),
    encoding="utf-8",
)
""",
            )
            errors = hygiene.check_reproducible_packaging(repo)
            self.assertTrue(
                any("Non-deterministic" in err for err in errors),
                errors,
            )

    def test_unsafe_zip_entries_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            zip_path = base / "unsafe.zip"
            with zipfile.ZipFile(zip_path, "w") as bundle:
                symlink_info = zipfile.ZipInfo("link.txt", (2026, 1, 1, 0, 0, 0))
                symlink_info.external_attr = (stat.S_IFLNK | 0o777) << 16
                bundle.writestr(symlink_info, "target")
                bundle.writestr("../escape.txt", "bad")
                bundle.writestr("/abs/path.txt", "bad")
                bundle.writestr("ignored-resources/private.json", "{}")
                bundle.writestr("home-assistant/situareness.json", "{}")

            errors = hygiene.inspect_zip_archive(zip_path)
            self.assertTrue(any("Symlink entry" in e for e in errors), errors)
            self.assertTrue(any("Path traversal" in e for e in errors), errors)
            self.assertTrue(any("Unsafe absolute" in e for e in errors), errors)
            self.assertTrue(
                any("ignored-resources/private.json" in e for e in errors), errors
            )
            self.assertTrue(
                any("home-assistant/situareness.json" in e for e in errors), errors
            )

            # Also verify check_reproducible_packaging catches unsafe entries even when deterministic.
            repo = base / "repo"
            _write_deterministic_package_script(
                repo,
                f"""
import argparse, hashlib, json, shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
target = args.output_dir / "bundle.zip"
shutil.copy2({str(zip_path)!r}, target)
sha = {hashlib.sha256(zip_path.read_bytes()).hexdigest()!r}
(args.output_dir / "manifest.json").write_text(
    json.dumps({{"version": "0.1.0", "bundles": [{{"name": "bundle.zip", "sha256": sha}}]}}),
    encoding="utf-8",
)
""",
            )
            pkg_errors = hygiene.check_reproducible_packaging(repo)
            self.assertTrue(any("Symlink entry" in e for e in pkg_errors), pkg_errors)
            self.assertTrue(any("Path traversal" in e for e in pkg_errors), pkg_errors)

    def test_docs_index_rejects_missing_tracked_file_and_ignores_globs_and_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "docs").mkdir()
            (repo / "docs/INDEX.md").write_text(
                "<!-- docs-sync\n"
                "code: `not/a/bullet.py`\n"
                "-->\n\n"
                "## docs/\n"
                "- `docs/existing.md` — Present.\n"
                "- `docs/adr/` — Directory reference ignored.\n"
                "- `docs/adr/*.md` — Glob reference ignored.\n"
                "- `docs/missing.md` — Missing file.\n",
                encoding="utf-8",
            )
            errors = hygiene.check_docs_index(
                repo, ["docs/INDEX.md", "docs/existing.md"]
            )
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("docs/missing.md", errors[0])


if __name__ == "__main__":
    unittest.main()
