#!/usr/bin/env python3
"""Apply a small, auditable Anker Port product overlay to a GPL upstream checkout.

The upstream runtime, Wine, FEX and graphics sources are retained unchanged.
This overlay is a fork-derived product build, not the independent SwiftUI shell.
"""
import pathlib
import plistlib
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
# Keep upstream's executable name, internal bundle identifiers and JIT protocol
# unchanged: renaming those without auditing native runtime references can break it.
print("Branded the app display name as Anker Port; retained GPL upstream runtime.")
