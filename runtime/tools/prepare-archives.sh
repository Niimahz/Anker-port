#!/usr/bin/env bash
set -euo pipefail
app="$1/app/Madeira"
build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT
sdk="$(xcrun --sdk iphoneos --show-sdk-path)"
common=(-DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT="$sdk" -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF)
git clone -q --depth 1 --branch v5.8.1 https://github.com/tukaani-project/xz.git "$build/xz"
cmake -S "$build/xz" -B "$build/xz-build" "${common[@]}" -DBUILD_TESTING=OFF
cmake --build "$build/xz-build" --target liblzma --parallel 4
git clone -q --depth 1 --branch v1.5.7 https://github.com/facebook/zstd.git "$build/zstd"
cmake -S "$build/zstd/build/cmake" -B "$build/zstd-build" "${common[@]}" \
  -DZSTD_BUILD_PROGRAMS=OFF -DZSTD_BUILD_SHARED=OFF -DZSTD_BUILD_TESTS=OFF -DZSTD_MULTITHREAD_SUPPORT=OFF
cmake --build "$build/zstd-build" --target libzstd_static --parallel 4
zstd="$(find "$build/zstd-build" -name libzstd.a -print -quit)"
test -f "$zstd"
git clone -q --depth 1 --branch v3.8.7 https://github.com/libarchive/libarchive.git "$build/archive"
lzma="$(find "$build/xz-build" -name liblzma.a -print -quit)"
cmake -S "$build/archive" -B "$build/build" "${common[@]}" \
  -DLIBLZMA_LIBRARY="$lzma" -DLIBLZMA_INCLUDE_DIR="$build/xz/src/liblzma/api" \
  -DENABLE_CAT=OFF -DENABLE_TAR=OFF -DENABLE_CPIO=OFF -DENABLE_UNZIP=OFF -DENABLE_INSTALL=OFF \
  -DHAVE_FORK=0 -DHAVE_VFORK=0 -DHAVE_POSIX_SPAWN=0 -DHAVE_POSIX_SPAWNP=0 \
  -DENABLE_LZMA=ON -DENABLE_ZLIB=ON -DENABLE_OPENSSL=OFF -DENABLE_NETTLE=OFF \
  -DENABLE_MBEDTLS=OFF -DENABLE_LIBB2=OFF -DENABLE_ZSTD=ON -DZSTD_LIBRARY="$zstd" -DZSTD_INCLUDE_DIR="$build/zstd/lib" -DENABLE_LZ4=OFF \
  -DENABLE_LZO=OFF -DENABLE_BZip2=OFF -DENABLE_LIBXML2=OFF -DENABLE_EXPAT=OFF \
  -DENABLE_ICONV=OFF -DENABLE_PCREPOSIX=OFF -DENABLE_PCRE2POSIX=OFF -DENABLE_TEST=OFF
grep -Eq '^#define HAVE_LIBZSTD 1' "$build/build/config.h"
cmake --build "$build/build" --target archive_static --parallel 4
libtool -static -o "$app/libankerarchives.a" "$build/build/libarchive/libarchive.a" "$lzma" "$zstd"
cp "$build/archive/libarchive/"{archive.h,archive_entry.h} runtime/ui/AnkerArchive.h runtime/ui/PortIPA.h "$app/"
echo '#include "PortIPA.h"' >> "$app/Madeira-Bridging-Header.h"
echo '#include "AnkerArchive.h"' >> "$app/Madeira-Bridging-Header.h"
python3 - "$1/app/Madeira.xcodeproj/project.pbxproj" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
s = p.read_text()
key = '"$(MADEIRA_VULKAN_LDFLAGS)"'
assert key in s
p.write_text(s.replace(key, key + ', "$(SRCROOT)/Madeira/libankerarchives.a", "-lz"'))
PY
