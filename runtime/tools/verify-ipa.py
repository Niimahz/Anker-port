#!/usr/bin/env python3
"""Check that the delivered IPA is a real branded runtime, not a UI-only shell."""
import argparse
import hashlib
import json
import plistlib
import struct
import tarfile
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
    executable = info.get("CFBundleExecutable")
    assert executable and "/" not in executable, "Invalid executable name"
    binary_path = prefix + executable
    binary_size = archive.getinfo(binary_path).file_size
    assert binary_size > 4096, "Empty native executable"
    with archive.open(binary_path) as binary:
        header = binary.read(32)
        assert len(header) == 32, "Truncated Mach-O header"
        magic, cpu, _, kind, commands, command_bytes, _, _ = struct.unpack("<8I", header)
        assert (magic, cpu, kind) == (0xfeedfacf, 0x0100000c, 2), "Expected an ARM64 Mach-O executable"
        assert 0 < commands <= command_bytes // 8 and command_bytes <= binary_size - 32, "Invalid Mach-O load commands"
        ios = False
        for _ in range(commands):
            command, size = struct.unpack("<II", binary.read(8))
            assert 8 <= size <= command_bytes, "Invalid Mach-O load command size"
            payload = binary.read(size - 8)
            assert len(payload) == size - 8, "Truncated Mach-O load command"
            if command == 0x32 and len(payload) >= 16:  # LC_BUILD_VERSION
                ios |= struct.unpack_from("<I", payload)[0] == 2  # PLATFORM_IOS
            command_bytes -= size
        assert command_bytes == 0 and ios, "Missing iPhoneOS build version"

    for item in ("arm64ec-windows/xtajit64.dll", "x86_64-vcruntime/vcruntime140.dll"):
        with archive.open(prefix + item) as dll:
            dos = dll.read(64)
            assert len(dos) == 64 and dos[:2] == b"MZ", f"Invalid DOS header: {item}"
            offset = struct.unpack_from("<I", dos, 60)[0]
            assert 64 <= offset <= archive.getinfo(prefix + item).file_size - 24, f"Invalid PE offset: {item}"
            dll.seek(offset)
            pe = dll.read(24)
            assert pe[:4] == b"PE\0\0" and struct.unpack_from("<H", pe, 22)[0] & 0x2000, f"Invalid PE DLL: {item}"
            if item.startswith("x86_64"):
                assert struct.unpack_from("<H", pe, 4)[0] == 0x8664, f"Expected x64 DLL: {item}"
    with archive.open(prefix + "prefix-template.tar.gz") as resource, tarfile.open(fileobj=resource, mode="r|gz") as template:
        assert any(member.isfile() and member.size for member in template), "Empty Wine prefix"
with args.ipa.open("rb") as ipa_file:
    digest = hashlib.sha256()
    for chunk in iter(lambda: ipa_file.read(1024 * 1024), b""):
        digest.update(chunk)
manifest = {
    "artifact": args.ipa.name,
    "sha256": digest.hexdigest(),
    "engine_revision": args.revision.strip(),
    "bundle_display_name": "Anker Port",
    "native_runtime_verified": True,
    "device_execution_verified": False,
}
output = args.ipa.with_suffix(".manifest.json")
output.write_text(json.dumps(manifest, indent=2) + "\n")
print(output.read_text())
