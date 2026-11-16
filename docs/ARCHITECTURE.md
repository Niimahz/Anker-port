# Architecture

Phase 0: SwiftUI -> security-scoped folder selection -> read-only PE parser -> JSON profile.

Future:
- Port selected Anker download and archive modules with proper attribution and dependency licenses.
- Integrate Madeira's pinned Wine/FEX/DXMT components inside the iOS process.
- Study PlayPort's runtime architecture and integrate only compatible, license-compliant components.
- Record real on-device results separately per runtime, including crash, performance and JIT state.
- Standalone IPA export must use the runtime build actually tested; it does not convert x86 Windows code to native ARM64.
- Respect GPL-3.0-or-later and game distribution rights.
