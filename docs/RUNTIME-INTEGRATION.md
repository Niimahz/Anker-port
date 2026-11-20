# Early runtime integration notes

This document records the prototype investigation before the native integration shipped. For the current build and runtime, see [Architecture](ARCHITECTURE.md) and [Native build](NATIVE-BUILD.md).

## Source-grounded reference
The upstream Wine host exposes ABI version 12 via `app/Sources/WineHost/include/wine_host.h` in playportdev/playport. Its contract is:

1. `wine_host_jit_pool_acquire` to acquire a debugger-blessed RX/RW JIT pool
2. `wine_host_init` with runtime directory, writable Wine prefix, log path and pool
3. `wine_host_session_start` to start an in-process wineserver/session root
4. `wine_host_session_launch` with DOS path and environment
5. `wine_host_session_wait` and stop/cleanup

The host is **not** a standalone library downloadable via Swift Package Manager. It needs statically linked `libwineserver.a`, `libntdll_unix.a`, `libwin32u_unix.a`, FEX DLLs, Wine PE DLLs, graphics drivers, and a compatible session root.

The source reference's `app/Package.swift` also links crypto, graphics and media libraries and stages generated binary artifacts before compilation. Madeira's `BUILDING.md` says its first complete native build can take several hours, including LLVM and FEX.

## Prototype implementation
`RuntimeLauncher.swift` defines an internal runtime boundary, validates that a user-supplied EXE is inside the imported game library and parses the PE architecture. It deliberately returns `unavailable` until native libraries and JIT integration exist.

## Original engineering plan
- Pin audited upstream source revisions; preserve full GPL license, modifications, and third-party notices.
- Reproduce the native build stages and generate compatible iOS static archives and guest DLL payloads.
- Implement a native C/Objective-C host target around the **actual** ABI and bundled session root.
- Add a display driver, controller and touch input routing, Metal/Vulkan translation and crash logs.
- Integrate debugger-authorized JIT, with a meaningful preflight and no false-positive status.
- Wire the launch button only after the native bridge is compiled and its runtime self-check passes.
- Test on an actual iOS device before claiming Windows game execution.

Do not use `Process`, `fork`, `exec`, `UIApplication.open`, or a URL scheme to pretend to run Windows EXEs.

## Product branding
The user-facing app is **Anker Port**. Upstream attribution remains in legal notices and corresponding source distribution. Names are not required in the primary gameplay UI.
