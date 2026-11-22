# Anker Port

**Bring your Windows games to iPhone.**

Start with a game archive and finish with a cover you can tap to play. Anker Port puts a browser, downloader, archive extractor and Windows game launcher on your iPhone. Want one game on its own? Package its files and runtime as a standalone iOS app.

**[Download the unsigned IPA](https://github.com/Niimahz/Anker-port/actions/runs/44961914737/artifacts/14732869981)** · [Browse builds](https://github.com/Niimahz/Anker-port/actions/workflows/build-ipa.yml) · [Report a game result](https://github.com/Niimahz/Anker-port/issues/new?template=game-report.yml)

![Anker Port — a Windows game library for your iPhone](docs/media/anker-port-cover.jpg)

## Browser · Find the game files

Open a developer’s download page in the built-in browser and follow its download link right there. Use the address bar to visit another site, go back to the release notes to check which edition you need, or reload the page before choosing a file.

## Downloads · Start with a link or a local archive

Already have the file URL? Paste the direct HTTPS link into **Downloads**. If you found the archive through the browser, open **Downloads → Files** to work with it after the transfer. If the game is already unpacked on your phone, import its folder directly.

## Extract · Keep the whole game together

Tap **Extract** to unpack ZIP and ZIP64, RAR and RAR5, 7z, TAR, TAR.GZ, TGZ or Gzip on-device. Import the resulting folder so the EXE can find its DLLs, audio and other assets. When a folder contains both a game and a setup utility, choose which EXE the library should launch.

## Library · Pick a game by its cover

Browse cover art in **Library → Collection**, open a title’s details, or return to a recently played game from **Home**. Steam title lookup helps identify a game when its archive or executable has an unfamiliar filename.

## Play · Launch from your collection

Tap a cover and press **Play** to launch a compatible Windows game locally through the Madeira-based runtime. Check JIT and Memory+ in **Settings** and open the gameplay or device settings when a title needs tuning. Game compatibility depends on the title, device and runtime configuration.

## IPA Export · Give a game its own app

Open **Export game IPA** on the game’s details page and confirm its folder. Anker Port bundles the game files with a runtime so you can sideload that game separately and open it from its own icon.

| Export option | What goes into the game app |
| --- | --- |
| **With JIT** | The Madeira-based runtime and the game’s launch profile, for compatible x86 and x64 Windows titles on a JIT-enabled setup. |
| **JITless · Native interpreter** | A native interpreter that runs locally without WebKit or JIT. This mode is experimental and supports 32-bit x86 executables. |

The finished unsigned IPA saves automatically in **Files → On My iPhone → Anker Port → Anker IPA**. Sign or sideload it using your usual setup. Allow space for the writable game copy created on first launch.

![From a Windows archive to in-library play or standalone IPA export](docs/media/game-to-ipa.svg)

## Get started

1. Sign in to GitHub and download the build artifact above. Open the ZIP in Files to find **AnkerPort-unsigned.ipa**. If the artifact has expired, open the builds page and choose the latest successful IPA build.
2. Import the IPA into your configured LiveContainer setup, or sign it with your iOS sideloading tool. For game execution, check **JIT** in Settings.
3. Open **Downloads** and paste a direct HTTPS file link, or use **Browser** to download from a website. You can also start with a game folder you already have in Files.
4. In **Downloads → Files**, find your archive and tap **Extract** if needed. Import the extracted game folder, keeping the EXE, DLLs and assets together. If the app finds multiple executables, choose the game’s main EXE.
5. Open **Library → Collection**, tap the game’s cover, then **Play**.

## Archive details

ZIP (including ZIP64), RAR/RAR5, 7z, TAR, TAR.GZ/TGZ and single-file Gzip. ZIP methods include Store, Deflate, LZMA, Zstandard (93), XZ (95) and PPMd. Password-protected archives and entries containing links have extraction limitations. A game that extracts successfully may still need runtime-specific settings to launch.

## Build and contribute

The macOS workflow builds the native iOS target and packages the unsigned IPA. The runtime source revision, integration scripts and packaging checks are tracked in this repository. Store clients, saves outside the game folder and globally installed prerequisites are separate.

[Native build guide](docs/NATIVE-BUILD.md) · [Architecture](docs/ARCHITECTURE.md) · [Issues](https://github.com/Niimahz/Anker-port/issues) · [Press kit and shareable artwork](docs/PRESS-KIT.md)

## Credits

**Nima HZ (@Niimahz)** created Anker Port. The native runtime comes from Will Faust’s Madeira project and its contributors, including upstream work on Wine, FEX and DXMT. Archive extraction uses libarchive, XZ and Zstandard. The standalone interpreter uses Boxedwine and SDL. Component licenses and upstream notices apply to their respective code. The app includes contributor credits under **Settings → App → Credits**.

[Anker Game Downloader](https://github.com/Niimahz/Anker_build) · [Madeira source used by this build](https://github.com/willfaust/Madeira/tree/fbad430410b4075192166172447c859714726de9)
