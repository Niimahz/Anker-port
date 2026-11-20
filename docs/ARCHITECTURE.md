# Architecture

The distributed IPA is built from a pinned Madeira source tree. Anker Port applies its native workspace and archive integration before compiling that tree for iOS.

| Layer | Source | Responsibility |
| --- | --- | --- |
| Workspace | [AnkerWorkspace.swift](../runtime/ui/AnkerWorkspace.swift), [workspace overlay](../runtime/ui/workspace_overlay.py) | Home, navigation, cover-art collection, settings presentation and WebKit downloads |
| Import and downloads | [integration script](../runtime/tools/integrate-upstream.py) | Direct HTTPS downloads, archive handling, game-folder import and library registration |
| Archive reader | [archive bridge](../runtime/ui/AnkerArchive.h), [dependency build](../runtime/tools/prepare-archives.sh) | Decode supported archives and write entries into staging |
| Game session | [pinned Madeira source](https://github.com/willfaust/Madeira/tree/fbad430410b4075192166172447c859714726de9) | Windows runtime, translation, display and JIT/session handling |
| Packaging | [IPA workflow](../.github/workflows/build-ipa.yml) | Compile, check runtime payload and publish a downloadable artifact |

The SwiftUI sources under App also document earlier development of the downloader and inspection shell. For the distributed native app, follow the integration pipeline above. Standalone game-specific IPA export remains a roadmap item.
