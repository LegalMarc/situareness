"""Create deterministic, explicitly enumerated installation bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
EXTENSION_FILES = (
    "background.js",
    "defaults/config.json",
    "lib/collector.js",
    "lib/config.js",
    "lib/normalize.js",
    "manifest.json",
    "offscreen.html",
    "offscreen.js",
    "room.css",
    "room.html",
    "room.js",
    "ui/helpers.mjs",
)
HA_FILES = (
    "__init__.py",
    "collector.py",
    "config.py",
    "config_flow.py",
    "const.py",
    "delivery.py",
    "domain.py",
    "manifest.json",
    "sensor.py",
    "strings.json",
)


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def validate() -> str:
    version = read_json("package.json")["version"]
    for name in (
        "extension/manifest.json",
        "custom_components/situareness/manifest.json",
    ):
        if read_json(name).get("version") != version:
            raise SystemExit(f"Version mismatch in {name}")
    config = read_json("extension/defaults/config.json")
    if (
        config.get("live_actions_enabled") is not False
        or config.get("enrolled_iphones") != []
    ):
        raise SystemExit("Unsafe browser defaults")
    for location in config.get("locations", []):
        if (
            location.get("household_exposure") is not None
            or location.get("google_speaker_targets") != []
            or location.get("horn_targets") != []
        ):
            raise SystemExit("Browser defaults contain private household configuration")
    private_example = read_json("home-assistant/situareness.example.json")
    if (
        private_example.get("live_enabled") is not False
        or private_example.get("commissioning_passed") is not False
        or private_example.get("phones") != []
        or private_example.get("tts_entity") is not None
        or private_example.get("approved_rules") != {}
        or private_example.get("states") != ["NY", "DC"]
        or not isinstance(private_example.get("locations"), dict)
        or set(private_example["locations"]) != {"nyc_sample", "washington_dc_sample"}
        or any(location != {} for location in private_example["locations"].values())
        or set(private_example)
        != {
            "states",
            "locations",
            "approved_rules",
            "phones",
            "tts_entity",
            "live_enabled",
            "commissioning_passed",
        }
    ):
        raise SystemExit("Unsafe Home Assistant example")
    return version


def sources(directory: str, names: tuple[str, ...], prefix: str) -> dict[str, Path]:
    result = {}
    for name in names:
        path = ROOT / directory / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"Required package source missing or a symlink: {path}")
        result[f"{prefix}/{name}"] = path
    return result


def make_bundle(directory: Path, name: str, files: dict[str, Path]) -> dict:
    target = directory / name
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for archive_name, file in sorted(files.items()):
            if file.is_symlink() or not file.is_file():
                raise SystemExit(
                    f"Required package source missing or a symlink: {file}"
                )
            info = zipfile.ZipInfo(archive_name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, file.read_bytes())
    with zipfile.ZipFile(target) as bundle:
        if bundle.testzip() is not None:
            raise SystemExit(f"Archive integrity failed: {name}")
    return {
        "name": name,
        "files": len(files),
        "bytes": target.stat().st_size,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    version = validate()
    extension = sources("extension", EXTENSION_FILES, "situareness-extension")
    extension["README.md"] = ROOT / "docs/extension-quickstart.md"
    ha = sources(
        "custom_components/situareness", HA_FILES, "custom_components/situareness"
    )
    ha["README.md"] = ROOT / "home-assistant/README.md"
    ha["home-assistant/situareness.example.json"] = (
        ROOT / "home-assistant/situareness.example.json"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    bundles = [
        make_bundle(args.output_dir, f"situareness-extension-{version}.zip", extension),
        make_bundle(args.output_dir, f"situareness-home-assistant-{version}.zip", ha),
    ]
    (args.output_dir / "manifest.json").write_text(
        json.dumps({"version": version, "bundles": bundles}, indent=2) + "\n",
        encoding="utf-8",
    )
    for bundle in bundles:
        print(f"{bundle['name']}: {bundle['files']} files, SHA-256 {bundle['sha256']}")


if __name__ == "__main__":
    main()
