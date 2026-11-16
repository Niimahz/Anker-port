#!/usr/bin/env python3
"""Linux iOS cross-link capability probe; never fabricates an IPA."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

result = {"ios_arm64_macho_object": False, "ios_arm64_macho_linked": False,
          "ios_sdk_present": False, "ipa_built": False, "details": {}}
clang = shutil.which("clang")
lld = shutil.which("ld64.lld")
result["details"]["clang"] = clang
result["details"]["ld64.lld"] = lld
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "main.c"
    source.write_text("int main(void) { return 0; }" + chr(10))
    obj = root / "main.o"
    if clang:
        command = [clang, "-target", "arm64-apple-ios15.0", "-ffreestanding", "-c", str(source), "-o", str(obj)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=30)
        result["ios_arm64_macho_object"] = p.returncode == 0 and obj.is_file()
        result["details"]["compile"] = (p.stderr or p.stdout)[-2000:]
    if result["ios_arm64_macho_object"] and lld:
        command = [lld, "-arch", "arm64", "-platform_version", "ios", "15.0", "15.0",
                   "-e", "_main", "-o", str(root / "probe"), str(obj)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=30)
        result["ios_arm64_macho_linked"] = p.returncode == 0 and (root / "probe").is_file()
        result["details"]["link"] = (p.stderr or p.stdout)[-2000:]
Path("AnkerPort-iOS-Link-Probe.json").write_text(json.dumps(result, indent=2) + chr(10))
print(json.dumps(result, indent=2))
if not result["ios_arm64_macho_object"]:
    raise SystemExit("iOS arm64 object compilation failed")
