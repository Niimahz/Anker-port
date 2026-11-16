# Native Windows runtime bridge (source integration)

This directory contains a real C ABI adapter for the in-process Wine host contract, not a mock game executor. It is intentionally **not** part of the ordinary SwiftUI target until the native dependency build succeeds.

## Required inputs

- `wine_host.h` and implementation from the pinned upstream source.
- iOS native static archives: wineserver, ntdll Unix, win32u Unix, graphics, crypto and other host dependencies.
- Wine PE DLL runtime payload, FEX translator DLLs, display driver and session root.
- Debugger-authorized JIT RX/RW memory pool.

The upstream build requires a large native toolchain and may take hours. See `docs/RUNTIME-INTEGRATION.md`. The separate source checkout workflow can verify the provenance of these inputs.

## ABI

`anker_runtime_initialize` validates pointers and the upstream ABI version, then invokes `wine_host_init`. `anker_runtime_start_session`, `anker_runtime_launch` and `anker_runtime_wait` delegate to the real native host functions. None are stubbed to return success.

## Licensing

GPL-3.0-or-later. When distributing a binary linked to the upstream host, publish corresponding source and applicable notices. The consumer-facing application may use its own branding.
