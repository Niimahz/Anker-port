#!/usr/bin/env bash
set -euo pipefail
STAGE="${1:?Usage: verify-native.sh STAGED_DIRECTORY}"
for file in \
  lib/libntdll_unix.a lib/libwineserver.a lib/libwin32u_unix.a \
  lib/libdxmt_combined.a lib/libFEXCore.a lib/libFEXCore_Base.a \
  Runtime/arm64ec-windows/xtajit64.dll \
  Runtime/prefix-template.tar.gz Runtime.entitlements; do
  test -s "$STAGE/$file" || { echo "Missing or empty $file" >&2; exit 1; }
done
echo "Native Wine/FEX/DXMT staging checks passed"
