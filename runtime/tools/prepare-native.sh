#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UPSTREAM="${1:-$ROOT/native-src}"
DEST="${2:-$ROOT/runtime/staged}"
APP="$UPSTREAM/app/Madeira"
FEX="$UPSTREAM/FEX/build-ios"
required=(
  "$APP/libntdll_unix.a"
  "$APP/libwineserver.a"
  "$APP/libwin32u_unix.a"
  "$APP/libdxmt_combined.a"
  "$APP/arm64ec-windows/xtajit64.dll"
  "$APP/prefix-template.tar.gz"
  "$FEX/FEXCore/Source/libFEXCore.a"
  "$FEX/FEXCore/Source/libFEXCore_Base.a"
)
for file in "${required[@]}"; do
  [[ -s "$file" ]] || { echo "Missing/empty native component: $file" >&2; exit 1; }
done
mkdir -p "$DEST/lib" "$DEST/Runtime"
for name in libntdll_unix.a libwineserver.a libwin32u_unix.a libdxmt_combined.a libmadeira_rppairing.a libgnutls.a libhogweed.a libnettle.a libgmp.a; do
  [[ ! -s "$APP/$name" ]] || cp "$APP/$name" "$DEST/lib/"
done
for spec in \
  "FEXCore/Source/libFEXCore.a:libFEXCore.a" \
  "FEXCore/Source/libFEXCore_Base.a:libFEXCore_Base.a" \
  "External/fmt/libfmt.a:libfmt.a" \
  "External/cephes/libcephes_128bit.a:libcephes_128bit.a"; do
  src="${spec%%:*}"
  dst="${spec##*:}"
  [[ ! -s "$FEX/$src" ]] || cp "$FEX/$src" "$DEST/lib/$dst"
done
for item in arm64ec-windows aarch64-windows i386-windows nls x86_64-vcruntime prefix-template.tar.gz; do
  if [[ -e "$APP/$item" ]]; then
    ditto "$APP/$item" "$DEST/Runtime/$item"
  fi
done
cp "$APP/Madeira.entitlements" "$DEST/Runtime.entitlements"
test -s "$DEST/lib/libFEXCore.a"
test -s "$DEST/Runtime/arm64ec-windows/xtajit64.dll"
echo "Staged native libraries and guest runtime under $DEST"
