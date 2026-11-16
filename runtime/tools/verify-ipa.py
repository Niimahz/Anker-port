#!/usr/bin/env python3
"""Check that the delivered IPA is a real branded runtime, not a UI-only shell."""
import argparse
import hashlib
import json
import plistlib
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("ipa", type=Path)
parser.add_argument("--revision", default="")
args = parser.parse_args()
assert args.ipa.is_file(), f"Missing IPA: {args.ipa}"
with zipfile.ZipFile(args.ipa) as archive:
    bad = archive.testzip()
    assert bad is None, f"Corrupt ZIP member: {bad}"
    apps = {name.split("/")[1] for name in archive.namelist()
            if name.startswith("Payload/") and name.count("/") >= 2}
    assert len(apps) == 1, f"Expected exactly one app, found {apps}"
    prefix = f"Payload/{next(iter(apps))}/"
    info = plistlib.loads(archive.read(prefix + "Info.plist"))
    assert info.get("CFBundleDisplayName") == "Anker Port", "Wrong display name"
    required = [
        "prefix-template.tar.gz",
        "arm64ec-windows/xtajit64.dll",
        "x86_64-vcruntime/vcruntime140.dll",
    ]
    for item in required:
        data = archive.read(prefix + item)
        assert data, f"Empty runtime resource: {item}"
        if item.endswith(".dll"):
            assert data.startswith(b"MZ"), f"Invalid PE header: {item}"
    executable = info.get("CFBundleExecutable")
    assert executable, "Missing executable key"
    assert len(archive.read(prefix + executable)) > 4096, "Empty native executable"
manifest = {
    "artifact": args.ipa.name,
    "sha256": hashlib.sha256(args.ipa.read_bytes()).hexdigest(),
    "engine_revision": args.revision.strip(),
    "bundle_display_name": "Anker Port",
    "native_runtime_verified": True,
    "device_execution_verified": False,
}
output = args.ipa.with_suffix(".manifest.json")
output.write_text(json.dumps(manifest, indent=2) + "\n")
print(output.read_text())
