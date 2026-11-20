# Anker Port

![Anker Port — a Windows game library for your iPhone](docs/media/anker-port-cover.jpg)

Download a Windows game archive, extract it on your iPhone, and add its executable to a cover-art library. Anker Port brings Anker’s download and import workflow into a native iOS launcher built on Madeira. You supply the game files. Launch compatibility depends on the game, device and JIT setup.

**[Download the unsigned IPA](https://github.com/Niimahz/Anker-port/actions/runs/44680760800/artifacts/14611992704)** · [Browse builds](https://github.com/Niimahz/Anker-port/actions/workflows/build-ipa.yml) · [Report a game result](https://github.com/Niimahz/Anker-port/issues/new?template=game-report.yml)

## Get started

1. Sign in to GitHub and download the build artifact above. Open the ZIP in Files to find **AnkerPort-unsigned.ipa**. GitHub lists this artifact through **December 4, 2026**. The builds page lists newer successful runs.
2. Import the IPA into your configured LiveContainer setup, or sign it with your iOS sideloading tool. For game execution, check **JIT** in Settings.
3. Open **Downloads** and paste a direct HTTPS file link, or use **Browser** to download from a website. You can also start with a game folder you already have in Files.
4. In **Downloads → Files**, find your archive and tap **Extract** if needed. Import the extracted game folder, keeping the EXE, DLLs and assets together. If the app finds multiple executables, choose the game’s main EXE.
5. Open **Library → Collection**, tap the game’s cover, then **Play**.

## Inside the app

| Destination | What you can do |
| --- | --- |
| Home | Return to a recently played game or jump to your library. |
| Library | Browse your collection by cover art, open game details, or switch to Sources. |
| Downloads | Save a direct download, extract an archive, import a folder or look up a title on Steam. |
| Browser | Download files through a website’s own links and navigate back to the source. |
| Settings | Check JIT and Memory+, then open controls grouped under Stores, Gameplay, Device and App. |

### Archive support

ZIP (including ZIP64), RAR/RAR5, 7z, TAR, TAR.GZ/TGZ and single-file Gzip. ZIP methods include Store, Deflate, LZMA, Zstandard (93), XZ (95) and PPMd. Password-protected archives and entries containing links have extraction limitations. A game that extracts successfully may still need runtime-specific settings to launch.

## Build and contribute

The macOS workflow builds the native iOS target and packages the unsigned IPA. The runtime source revision, integration scripts and packaging checks are tracked in this repository. A standalone IPA exporter for individual games remains a project goal.

[Native build guide](docs/NATIVE-BUILD.md) · [Architecture](docs/ARCHITECTURE.md) · [Issues](https://github.com/Niimahz/Anker-port/issues) · [Press kit and shareable artwork](docs/PRESS-KIT.md)

## Credits

**Nima HZ (@Niimahz)** created Anker Port. The native runtime comes from Will Faust’s Madeira project and its contributors, including upstream work on Wine, FEX and DXMT. Archive extraction uses libarchive, XZ and Zstandard. Component licenses and upstream notices apply to their respective code. The app includes contributor credits under **Settings → App → Credits**.

[Anker Game Downloader](https://github.com/Niimahz/Anker_build) · [Madeira source used by this build](https://github.com/willfaust/Madeira/tree/fbad430410b4075192166172447c859714726de9)
