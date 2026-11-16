#!/usr/bin/env bash
set -euo pipefail
STAGE="${1:?Usage: verify-native.sh STAGED_DIRECTORY}"
for file in \
  lib/libntdll_unix.a lib/libwineserver.a lib/libwin32u_unix.a \
  lib/libdxmt_combined.a Runtime/arm64ec-windows/xtajit64.dll \
  Runtime/prefix-template.tar.gz; do
  test -s "$STAGE/$file" || { echo "Missing or empty $file" >&2; exit 1; }
done
echo "Native runtime staging checks passed"
