# Anker Port — iOS Windows Game Studio

An independent iOS game library and compatibility project. The goal is to launch user-supplied Windows games on-device, then optionally build standalone game IPAs **after real on-device testing**.

## Current implemented source
- SwiftUI Library, Downloads and Analyzer tabs
- Anker's concurrent/segmented downloader and background download manager
- Archive import from Files; ZIP extraction via ZIPFoundation and other supported archive formats via LibArchive
- Local game folders and per-game inspection
- PE EXE/DLL analysis (architecture and imported DLLs), BAT/CMD discovery
- Compatibility profile JSON export

## Not implemented or verified
- Wine/FEX/DXMT Windows game execution: **not yet integrated**
- Game-specific standalone IPA packaging: **not yet integrated**
- iPhone runtime validation: **not tested**
- Successful iOS compilation: pending GitHub Actions result

The launcher is deliberately disabled rather than pretending to run a Windows executable.

## Build
The GitHub Actions workflow `.github/workflows/build-ipa.yml` generates an unsigned iOS IPA when the macOS runner completes successfully. Local build: `cd App && xcodegen generate` then build in Xcode with signing configured.

## License and attribution
Some source modules were adapted from the user's Anker Game Downloader project. Third-party dependencies retain their own licenses. Future integration of GPL-3.0-or-later runtime code must comply with corresponding source distribution and notice requirements. Runtime implementation names may be hidden from normal gameplay UI, but legal attribution cannot be removed.

## Engineering milestones
1. Verify compilation, resolve errors, test downloader/extraction.
2. Bring in selected Anker browser and advanced archive features.
3. Build in-process Windows runtime with Wine, x86 translation, and graphics translation; verify signing/JIT behavior.
4. Launch real games and record device diagnostics.
5. Add reproducible per-game IPA packaging after stable execution.
