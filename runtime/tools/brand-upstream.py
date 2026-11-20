#!/usr/bin/env python3
"""Apply a small, auditable Anker Port product overlay to a GPL upstream checkout.

The upstream runtime, Wine, FEX and graphics sources are retained unchanged.
This overlay is a fork-derived product build, not the independent SwiftUI shell.
"""
import pathlib
import plistlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 runtime/tools/brand-upstream.py UPSTREAM_ROOT")
root = pathlib.Path(sys.argv[1]).resolve()
info = root / "app/Madeira/Info.plist"
project = root / "app/Madeira.xcodeproj/project.pbxproj"
assert info.is_file() and project.is_file(), "expected upstream iOS Xcode project"
with info.open("rb") as f:
    data = plistlib.load(f)
assert data.get("CFBundleDisplayName") in ("Madeira", "Anker Port"), "unexpected upstream plist"
data["CFBundleDisplayName"] = "Anker Port"
data["NSLocalNetworkUsageDescription"] = (
    "Anker Port uses the local network for device pairing and downloading game content."
)
with info.open("wb") as f:
    plistlib.dump(data, f, sort_keys=False)
# The host and both helper targets derive their identifiers from this setting.
settings, count = re.subn(
    r"(?m)^(\s*MADEIRA_BUNDLE_IDENTIFIER = )(?:com\.willfaust\.madeora|app\.ankerport\.ios);$",
    r"\g<1>app.ankerport.ios;", project.read_text()
)
assert count == 2, "Expected both Debug and Release bundle identifier settings"
project.write_text(settings)
print("Branded Anker Port with bundle identifier app.ankerport.ios")
