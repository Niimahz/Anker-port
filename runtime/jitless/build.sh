#!/usr/bin/env bash
set -euo pipefail
# Cross-compile the normal CPU interpreter. No dynamic CPU, FEX or WebKit.
source_dir=$(cd "$1" && pwd)
out=$(mkdir -p "$2" && cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
cd "$source_dir"
sdl="$source_dir/lib/sdl2"
xcodebuild -project "$sdl/Xcode-iOS/SDL/SDL.xcodeproj" -scheme libSDL-iOS \
  -configuration Release -sdk iphoneos ARCHS=arm64 IPHONEOS_DEPLOYMENT_TARGET=17.0 \
  CONFIGURATION_BUILD_DIR="$out/sdl" CODE_SIGNING_ALLOWED=NO build
sdk=$(xcrun --sdk iphoneos --show-sdk-path)
flags=(-arch arm64 -isysroot "$sdk" -miphoneos-version-min=17.0 -O2)
cpp=(-include algorithm -std=c++17 -Iinclude -I"$sdl/include" -DSDL2 -DBOXEDWINE_DISABLE_UI -DBOXEDWINE_ZLIB
     -DBOXEDWINE_POSIX -DBOXEDWINE_HAS_SETJMP -DSIMDE_SSE2_NO_NATIVE)
mkdir -p "$out/obj"
python3 - <<'PY'
from pathlib import Path
p = Path("platform/sdl/knativesystem.cpp")
s = p.read_text().replace("#ifndef __TEST", "#if 0 // standalone SDL_main supplied by Anker", 1)
p.write_text(s)
p = Path("platform/linux/platform.cpp")
s = p.read_text().replace("#ifndef __MACH__\nint getPixelFormats", "#if 1\nint getPixelFormats", 1)
p.write_text(s)
PY
sources=(source/sdl/*.cpp source/sdl/singleThreaded/*.cpp platform/sdl/*.cpp platform/linux/platform.cpp
    source/emulation/cpu/*.cpp source/emulation/cpu/{normal,common}/*.cpp source/emulation/softmmu/*.cpp
    source/io/*.cpp source/kernel/*.cpp source/kernel/{devs,proc,sys,loader}/*.cpp source/util/*.cpp source/opengl/*.cpp)
for src in "${sources[@]}"; do
    case "$src" in source/util/networkutils.cpp|source/util/threadutils.cpp) continue;; esac
    xcrun clang++ "${flags[@]}" "${cpp[@]}" -c "$src" -o "$out/obj/${src//\//_}.o"
done
for src in lib/zlib/contrib/minizip/{ioapi,unzip}.c; do
    xcrun clang "${flags[@]}" -DUSE_FILE32API -c "$src" -o "$out/obj/$(basename "$src").o"
done
sdl_lib=$(find "$out/sdl" -name libSDL2.a -print -quit)
frameworks=()
for framework in Foundation UIKit CoreGraphics QuartzCore CoreAudio AudioToolbox AVFoundation CoreMotion GameController Metal OpenGLES CoreBluetooth CoreHaptics; do
    frameworks+=(-framework "$framework")
done
xcrun clang++ "${flags[@]}" "${cpp[@]}" -fobjc-arc "$here/launcher.mm" "$out"/obj/*.o "$sdl_lib" \
    "${frameworks[@]}" -lz -o "$out/AnkerNative"
