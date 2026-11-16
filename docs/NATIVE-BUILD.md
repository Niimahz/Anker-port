# Native runtime build and staging

The SwiftUI-only Anker Port IPA cannot execute Windows programs. A separate
native runtime build is necessary.

## Source-based pipeline

1. The `build-native-runtime.yml` GitHub workflow checks out the complete
   upstream source tree and invokes its real Wine/FEX/DXMT build.
2. `runtime/tools/prepare-native.sh` stages native static libraries, Windows
   PE DLLs, JIT translator DLLs, prefix template and entitlement source.
3. `runtime/tools/verify-native.sh` checks required files are present.
4. A **future integrated target** must compile the native Wine host and
   Anker C adapter, link all native dependencies, package staged resources,
   set supported entitlements, and connect the native display/JIT/session APIs.

The staged artifacts are not sufficient to link a working app by themselves.
In particular the upstream runtime uses a native display driver and process
bridge with a complex build graph. Do not ship the reference IPA as if it were
Anker Port, and do not enable Launch until the integrated binary exists.

The source project's runtime requires compliance with GPL and third-party
license notices.
