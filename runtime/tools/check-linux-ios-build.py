#!/usr/bin/env python3
"""Report build blockers rather than falsely labeling source archives as IPA files."""
import json
from pathlib import Path
import platform
import shutil
import sys
import subprocess
import tempfile

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
def probe_ios_object():
    """Compile a freestanding iOS arm64 object; does not imply linking is possible."""
    clang = shutil.which("clang")
    if not clang:
        return {"supported": False, "reason": "clang unavailable"}
    with tempfile.TemporaryDirectory() as tmp:
        source_file = Path(tmp) / "probe.c"
        object_file = Path(tmp) / "probe.o"
        source_file.write_text("int anker_ios_probe(void) { return 42; }" + chr(10))
        command = [clang, "-target", "arm64-apple-ios15.0", "-ffreestanding", "-c", str(source_file), "-o", str(object_file)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            return {"supported": result.returncode == 0 and object_file.is_file(),
                    "diagnostic": (result.stderr or result.stdout)[-1000:]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"supported": False, "reason": str(exc)}


report = {
    "host_os": platform.system(),
    "available_commands": {name: bool(shutil.which(name)) for name in ("swiftc", "clang", "cmake", "ninja", "xcodebuild", "xcrun", "ldid")},
    "upstream_build_requirements": requirements,
    "ios_arm64_object_probe": probe_ios_object(),
    "ios_sdk_path": None,
    "ipa_built": False,
    "conclusion": "A freestanding iOS object is not a linked iOS app. Upstream build-ipa.sh requires macOS/Xcode; no IPA was produced.",
}
Path("AnkerPort-Linux-Build-Feasibility.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not all(requirements.values()):
    raise SystemExit("Upstream project or integration missing required elements")
