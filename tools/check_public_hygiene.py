"""Verify public repository hygiene, secret absence, reproducible packaging, and docs index links."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_DIRS = frozenset(
    {
        "ignored-resources",
        "work",
        "dist",
        ".venv",
        "node_modules",
        "playwright-report",
        "test-results",
    }
)
FORBIDDEN_EXACT_PATHS = frozenset({"home-assistant/situareness.json"})

# Split PEM markers across separate literals so this file never matches its own regex.
_PEM_BEGIN = "-----BEGIN "
_PEM_END = "PRIVATE KEY-----"
PRIVATE_KEY_RE = re.compile(_PEM_BEGIN + r"[^\r\n]*" + _PEM_END)
GHP_RE = re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")
GITHUB_PAT_RE = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")
AKIA_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
BEARER_RE = re.compile(r"\bBearer\s+(?!<)([A-Za-z0-9._~+/=-]{16,})")

BEARER_PLACEHOLDER_PREFIXES = (
    "your-",
    "your_",
    "example",
    "placeholder",
    "redacted",
)

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
BULLET_LINE_RE = re.compile(r"^\s*-\s+")
BACKTICK_RE = re.compile(r"`([^`]+)`")


def _normalize_posix(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def git_tracked_files(root: Path) -> list[str]:
    """Return sorted POSIX-normalized tracked paths from `git ls-files`."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed in {root}: {stderr}")
    entries = [
        _normalize_posix(item.decode("utf-8", errors="surrogateescape"))
        for item in result.stdout.split(b"\x00")
        if item
    ]
    return sorted(entries)


def is_forbidden_path(rel_path: str) -> str | None:
    """Return a reason if `rel_path` matches a private or generated-artifact rule."""
    normalized = _normalize_posix(rel_path)
    pure = PurePosixPath(normalized)
    parts = pure.parts
    if not parts:
        return "empty path"

    for part in parts:
        if part in FORBIDDEN_DIRS:
            return f"forbidden directory component '{part}'"

    if normalized in FORBIDDEN_EXACT_PATHS:
        return f"forbidden private configuration '{normalized}'"

    name = parts[-1]
    if name == ".DS_Store":
        return "forbidden macOS metadata file '.DS_Store'"
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return f"forbidden environment file '{name}'"
    if name.endswith(".local.json"):
        return f"forbidden local override file '{name}'"
    if fnmatch.fnmatch(name, "*.sqlite*"):
        return f"forbidden SQLite file '{name}'"
    if fnmatch.fnmatch(name, "*.db*"):
        return f"forbidden database file '{name}'"
    return None


def check_forbidden_tracked_paths(tracked_paths: Iterable[str]) -> list[str]:
    """Check tracked paths against forbidden private and generated path rules."""
    errors: list[str] = []
    for rel_path in tracked_paths:
        reason = is_forbidden_path(rel_path)
        if reason is not None:
            errors.append(f"Forbidden tracked path '{rel_path}': {reason}")
    return errors


def _is_placeholder_bearer(token: str) -> bool:
    lowered = token.lower()
    return lowered.startswith(BEARER_PLACEHOLDER_PREFIXES)


def scan_text_for_secrets(text: str, rel_path: str) -> list[str]:
    """Scan UTF-8 text lines for credential or private-key patterns."""
    findings: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if PRIVATE_KEY_RE.search(line):
            findings.append(f"Potential private key header in '{rel_path}:{line_no}'")
        if GHP_RE.search(line):
            findings.append(f"Potential GitHub classic token in '{rel_path}:{line_no}'")
        if GITHUB_PAT_RE.search(line):
            findings.append(
                f"Potential GitHub fine-grained token in '{rel_path}:{line_no}'"
            )
        if AKIA_RE.search(line):
            findings.append(f"Potential AWS access key ID in '{rel_path}:{line_no}'")
        for match in BEARER_RE.finditer(line):
            token = match.group(1)
            if not _is_placeholder_bearer(token):
                findings.append(f"Potential Bearer token in '{rel_path}:{line_no}'")
    return findings


def check_tracked_secrets(root: Path, tracked_paths: Iterable[str]) -> list[str]:
    """Scan tracked UTF-8 text files (skipping binaries and symlinks) for secrets."""
    findings: list[str] = []
    for rel_path in tracked_paths:
        target = root / rel_path
        if target.is_symlink() or not target.is_file():
            continue
        raw = target.read_bytes()
        if b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text_for_secrets(text, rel_path))
    return findings


def inspect_zip_archive(zip_path: Path) -> list[str]:
    """Inspect a ZIP archive for integrity, symlinks, path traversal, and forbidden paths."""
    errors: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as bundle:
        bad_member = bundle.testzip()
        if bad_member is not None:
            errors.append(
                f"ZIP integrity check failed in '{zip_path.name}' on '{bad_member}'"
            )
        for info in bundle.infolist():
            entry_name = info.filename
            if not entry_name:
                errors.append(f"Empty ZIP entry name in '{zip_path.name}'")
                continue
            if (
                entry_name.startswith("/")
                or "\\" in entry_name
                or (len(entry_name) >= 2 and entry_name[1] == ":")
            ):
                errors.append(
                    f"Unsafe absolute or backslash path '{entry_name}' in '{zip_path.name}'"
                )
                continue
            pure = PurePosixPath(entry_name)
            if ".." in pure.parts:
                errors.append(
                    f"Path traversal entry '{entry_name}' in '{zip_path.name}'"
                )
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                errors.append(f"Symlink entry '{entry_name}' in '{zip_path.name}'")
            reason = is_forbidden_path(entry_name)
            if reason is not None:
                errors.append(
                    f"Forbidden path '{entry_name}' in '{zip_path.name}': {reason}"
                )
    return errors


def _run_package(package_script: Path, output_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(package_script), "--output-dir", str(output_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit {result.returncode}"
        )
        raise RuntimeError(f"{package_script} failed: {detail}")


def check_reproducible_packaging(
    root: Path, package_script: Path | None = None
) -> list[str]:
    """Run tools/package.py twice and verify deterministic digests, manifest parity, and ZIP safety."""
    script = package_script if package_script is not None else root / "tools/package.py"
    if not script.is_file():
        return [f"Missing packaging script: {script}"]

    errors: list[str] = []
    with (
        tempfile.TemporaryDirectory() as dir_one,
        tempfile.TemporaryDirectory() as dir_two,
    ):
        out_one = Path(dir_one)
        out_two = Path(dir_two)
        try:
            _run_package(script, out_one)
            _run_package(script, out_two)
        except RuntimeError as exc:
            return [str(exc)]

        manifest_one_path = out_one / "manifest.json"
        manifest_two_path = out_two / "manifest.json"
        if not manifest_one_path.is_file() or not manifest_two_path.is_file():
            return ["Packaging output missing manifest.json"]

        manifest_one_bytes = manifest_one_path.read_bytes()
        manifest_two_bytes = manifest_two_path.read_bytes()
        if manifest_one_bytes != manifest_two_bytes:
            errors.append("Non-deterministic manifest.json across two packaging runs")

        manifest_one = json.loads(manifest_one_bytes.decode("utf-8"))
        manifest_two = json.loads(manifest_two_bytes.decode("utf-8"))
        if manifest_one != manifest_two:
            errors.append("Parsed manifest.json mismatch across two packaging runs")

        zips_one = sorted(p.name for p in out_one.glob("*.zip"))
        zips_two = sorted(p.name for p in out_two.glob("*.zip"))
        if not zips_one:
            errors.append("Packaging produced no ZIP archives")
            return errors
        if zips_one != zips_two:
            errors.append(f"Packaging ZIP list mismatch: {zips_one} vs {zips_two}")
            return errors

        bundle_digests = {
            bundle["name"]: bundle.get("sha256")
            for bundle in manifest_one.get("bundles", [])
            if isinstance(bundle, dict) and "name" in bundle
        }

        for name in zips_one:
            bytes_one = (out_one / name).read_bytes()
            bytes_two = (out_two / name).read_bytes()
            sha_one = hashlib.sha256(bytes_one).hexdigest()
            sha_two = hashlib.sha256(bytes_two).hexdigest()
            if sha_one != sha_two or bytes_one != bytes_two:
                errors.append(f"Non-deterministic ZIP '{name}': {sha_one} != {sha_two}")
            if name in bundle_digests and bundle_digests[name] != sha_one:
                errors.append(
                    f"manifest.json SHA-256 mismatch for '{name}': "
                    f"{bundle_digests[name]} != {sha_one}"
                )
            errors.extend(inspect_zip_archive(out_one / name))
            if bytes_one != bytes_two:
                errors.extend(inspect_zip_archive(out_two / name))
    return errors


def extract_index_doc_paths(index_text: str) -> list[str]:
    """Extract backticked file paths under `## ` section bullets in docs/INDEX.md."""
    cleaned = HTML_COMMENT_RE.sub("", index_text)
    in_section = False
    paths: list[str] = []
    seen: set[str] = set()

    for line in cleaned.splitlines():
        if line.startswith("## "):
            in_section = True
            continue
        if not in_section or not BULLET_LINE_RE.match(line):
            continue
        for token in BACKTICK_RE.findall(line):
            candidate = _normalize_posix(token.strip())
            if not candidate or any(ch.isspace() for ch in candidate):
                continue
            if candidate.endswith("/"):
                continue
            if any(glob_ch in candidate for glob_ch in "*?["):
                continue
            if candidate not in seen:
                seen.add(candidate)
                paths.append(candidate)
    return paths


def check_docs_index(root: Path, tracked_paths: Iterable[str]) -> list[str]:
    """Verify backticked repo file paths in docs/INDEX.md exist in git ls-files."""
    index_path = root / "docs/INDEX.md"
    if not index_path.is_file():
        return [f"Missing docs index file: {index_path}"]

    tracked_set = set(tracked_paths)
    referenced = extract_index_doc_paths(index_path.read_text(encoding="utf-8"))
    if not referenced:
        return ["No file references found under section bullets in docs/INDEX.md"]

    errors: list[str] = []
    for ref in referenced:
        if ref not in tracked_set:
            errors.append(
                f"docs/INDEX.md references '{ref}', which is not tracked in git ls-files"
            )
    return errors


def run_all_checks(root: Path) -> list[str]:
    """Run all public hygiene, secret, packaging, and docs-index checks."""
    tracked = git_tracked_files(root)
    errors: list[str] = []
    errors.extend(check_forbidden_tracked_paths(tracked))
    errors.extend(check_tracked_secrets(root, tracked))
    errors.extend(check_reproducible_packaging(root))
    errors.extend(check_docs_index(root, tracked))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        tracked = git_tracked_files(root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    errors.extend(check_forbidden_tracked_paths(tracked))
    errors.extend(check_tracked_secrets(root, tracked))
    errors.extend(check_reproducible_packaging(root))
    errors.extend(check_docs_index(root, tracked))

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    indexed_count = len(
        extract_index_doc_paths((root / "docs/INDEX.md").read_text(encoding="utf-8"))
    )
    print(
        f"Public hygiene passed: {len(tracked)} tracked files clean, "
        f"reproducible ZIP packaging verified, {indexed_count} docs/INDEX.md file links tracked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
