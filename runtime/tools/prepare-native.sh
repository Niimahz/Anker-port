#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UPSTREAM="${1:-$ROOT/native-src}"
DEST="${2:-$ROOT/runtime/staged}"
[[ -f "$UPSTREAM/app/Madeira/libntdll_unix.a" ]] || { echo "Missing native ntdll archive; build upstream first" >&2; exit 1; }
[[ -f "$UPSTREAM/app/Madeira/libwineserver.a" ]] || { echo "Missing native wineserver archive" >&2; exit 1; }
[[ -f "$UPSTREAM/app/Madeira/libwin32u_unix.a" ]] || { echo "Missing native win32u archive" >&2; exit 1; }
[[ -f "$UPSTREAM/app/Madeira/libdxmt_combined.a" ]] || { echo "Missing native graphics archive" >&2; exit 1; }
[[ -f "$UPSTREAM/app/Madeira/arm64ec-windows/xtajit64.dll" ]] || { echo "Missing x64 translation DLL" >&2; exit 1; }
mkdir -p "$DEST/lib" "$DEST/Runtime"
for name in libntdll_unix.a libwineserver.a libwin32u_unix.a libdxmt_combined.a libgnutls.a libhogweed.a libnettle.a libgmp.a; do
  if [[ -f "$UPSTREAM/app/Madeira/$name" ]]; then cp "$UPSTREAM/app/Madeira/$name" "$DEST/lib/"; fi
done
for item in arm64ec-windows aarch64-windows i386-windows nls prefix-template.tar.gz; do
  if [[ -e "$UPSTREAM/app/Madeira/$item" ]]; then
    ditto "$UPSTREAM/app/Madeira/$item" "$DEST/Runtime/$item"
  fi
done
cp "$UPSTREAM/app/Madeira/Madeira.entitlements" "$DEST/Runtime.entitlements"
find "$DEST/lib" -name '*.a' -size +0c | sort
test -s "$DEST/lib/libntdll_unix.a"
test -s "$DEST/Runtime/arm64ec-windows/xtajit64.dll"
echo "Staged native libraries and guest runtime under $DEST"
