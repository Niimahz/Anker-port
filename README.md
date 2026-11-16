# Anker Port Studio

Experimental iOS PC game inspection and compatibility-profile application. This initial scaffold does **not** run Windows games or build standalone game IPAs.

## Phase 0
- SwiftUI folder picker
- Read-only PE executable inspection: x86/x64/ARM64 and imported DLL names
- BAT/CMD discovery (never executed)
- JSON compatibility profile export (status: untested)
- Separate Madeira and PlayPort runtime adapter interfaces (integration pending)

## Build
Install XcodeGen, then run `cd App && xcodegen generate` on macOS. Open the generated Xcode project and configure signing. The project has not been compiled or device-tested yet.

## Roadmap
1. Reuse audited Anker download/archive code with attribution.
2. Integrate and validate Madeira Wine/FEX/DXMT in-process runtime.
3. Add PlayPort adapter after checking code and dependency compatibility.
4. Test real games on device and record crash/FPS results.
5. Implement standalone IPA export only after reliable runtime testing.

Madeira and PlayPort are GPL-3.0-or-later projects. Source reuse and distribution must comply with applicable licenses. Game files must be lawfully supplied.
