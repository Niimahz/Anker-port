#!/usr/bin/env python3
"""Report build blockers rather than falsely labeling source archives as IPA files."""
import json
from pathlib import Path
import platform
import shutil
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("native-src")
script = root / "tools/build-ipa.sh"
if not script.is_file():
    raise SystemExit("Missing Madeira build script")
source = script.read_text()
requirements = {
    "darwin_guard": 'uname -s' in source and "Darwin" in source,
    "xcodebuild": "xcodebuild" in source,
    "xcrun": "xcrun" in source,
    "homebrew": "brew" in source,
    "native_project": (root / "app/Madeira.xcodeproj/project.pbxproj").is_file(),
    "integrated_ui": "ANKER_PORT_INTEGRATION_V1" in (root / "app/Madeira/MadeiraApp.swift").read_text(),
}
report = {
    "host_os": platform.system(),
    "available_commands": {name: bool(shutil.which(name)) for name in ("swiftc", "clang", "cmake", "ninja", "xcodebuild", "xcrun", "ldid")},
    "upstream_build_requirements": requirements,
    "ipa_built": False,
    "conclusion": "Upstream build-ipa.sh requires macOS/Xcode; Linux source preparation is not an iOS IPA build.",
}
Path("AnkerPort-Linux-Build-Feasibility.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not all(requirements.values()):
    raise SystemExit("Upstream project or integration missing required elements")
