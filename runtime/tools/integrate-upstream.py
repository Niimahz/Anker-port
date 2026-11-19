#!/usr/bin/env python3
"""Inject Anker download entry into the real Madeira app, retaining its Wine launch path."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: integrate-upstream.py UPSTREAM_ROOT")
source = Path(sys.argv[1]) / "app/Madeira/MadeiraApp.swift"
original = source.read_text()
if "import UniformTypeIdentifiers" not in original:
    original = "import UniformTypeIdentifiers\n" + original
marker = "            ContentView()\n"
assert marker in original or "// ANKER_PORT_INTEGRATION_V1" in original, "upstream entry point changed"
if "// ANKER_PORT_INTEGRATION_V1" in original:
    print("Anker download overlay already integrated")
    raise SystemExit(0)
original += r'''
// ANKER_PORT_INTEGRATION_V1
@MainActor
private final class AnkerDownloadModel: ObservableObject {
    @Published var address = ""
    @Published var status = "Ready to download"
    @Published var downloadedBytes: Int64 = 0
    @Published var expectedBytes: Int64 = 0
    @Published var busy = false
    @Published var saved: URL?
    @Published var files: [URL] = []
    @Published var executableCandidates: [URL] = []
    @Published var steamQuery = ""
    @Published var steamGames: [AnkerSteamGame] = []
    @Published var steamError = ""
    @Published var steamBusy = false
    @Published var configExecutable: URL?
    @Published var configText = ""
    @Published var configStatus = ""


    private var directory: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("AnkerDownloads", isDirectory: true)
    }

    var validatedURL: URL? {
        guard let url = URL(string: address.trimmingCharacters(in: .whitespacesAndNewlines)),
              let scheme = url.scheme?.lowercased(),
              scheme == "https",
              url.host != nil, url.user == nil, url.password == nil else { return nil }
        return url
    }

    func refresh() {
        files = (try? FileManager.default.contentsOfDirectory(
            at: directory, includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]))?
            .filter { $0.isFileURL && !$0.hasDirectoryPath }
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending } ?? []
    }

    private func addToLibrary(_ executable: URL) throws {
        let entry = try LibraryModel.inspect(executable)
        let library = LibraryModel.shared
        library.save(entry)
        guard library.entries.contains(where: { $0.id == entry.id }) else {
            throw NSError(domain: "AnkerImport", code: 1, userInfo: [
                NSLocalizedDescriptionKey: library.error ?? "Anker Port could not register the game."
            ])
        }
    }

    // Reuse Madeira's PE inspector and native library persistence.
    func registerExecutable(_ file: URL) {
        guard !busy else { return }
        guard (try? file.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink) != true else {
            status = "Symbolic-link executables cannot be imported."
            return
        }
        guard ((try? FileManager.default.attributesOfItem(atPath: file.path)[.size] as? NSNumber)?.int64Value ?? 0) > 0 else {
            status = "The executable is empty or unreadable."
            return
        }
        guard file.pathExtension.lowercased() == "exe" else {
            status = "Only Windows .exe files can be registered."
            return
        }
        do {
            let targetFolder = LibraryModel.drive.appendingPathComponent("Games/AnkerImports", isDirectory: true)
            try FileManager.default.createDirectory(at: targetFolder, withIntermediateDirectories: true)
            let target = targetFolder.appendingPathComponent(UUID().uuidString + "-" + file.lastPathComponent)
            try FileManager.default.copyItem(at: file, to: target)
            do {
                try addToLibrary(target)
                status = "Added to your game library."
            } catch {
                try? FileManager.default.removeItem(at: target)
                throw error
            }
        } catch {
            status = "Library import failed: " + error.localizedDescription
        }
    }

    // Preserve full installed game directory, DLLs and asset paths.
    func importGameFolder(_ source: URL) {
        guard !busy else { return }
        busy = true
        executableCandidates = []
        configExecutable = nil
        configStatus = ""
        defer { busy = false }
        let accessed = source.startAccessingSecurityScopedResource()
        defer { if accessed { source.stopAccessingSecurityScopedResource() } }
        do {
            var isDirectory: ObjCBool = false
            guard FileManager.default.fileExists(atPath: source.path, isDirectory: &isDirectory),
                  isDirectory.boolValue else {
                status = "Select an extracted game folder."
                return
            }
            let destination = LibraryModel.drive
                .appendingPathComponent("Games/AnkerImports", isDirectory: true)
                .appendingPathComponent(UUID().uuidString + "-" + source.lastPathComponent, isDirectory: true)
            try FileManager.default.createDirectory(at: destination.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true)
            do {
                try FileManager.default.copyItem(at: source, to: destination)
            } catch {
                try? FileManager.default.removeItem(at: destination)
                throw error
            }
            var candidates: [URL] = []
            if let walker = FileManager.default.enumerator(at: destination,
                    includingPropertiesForKeys: [.isRegularFileKey],
                    options: [.skipsHiddenFiles]) {
                while let file = walker.nextObject() as? URL {
                    if (try? file.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink) == true {
                        walker.skipDescendants()
                        continue
                    }
                    if file.pathExtension.lowercased() == "exe",
                       (try? file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true {
                        candidates.append(file)
                        if candidates.count >= 500 { break }
                    }
                }
            }
            if candidates.count == 1, let executable = candidates.first {
                do {
                    try addToLibrary(executable)
                } catch {
                    try? FileManager.default.removeItem(at: destination)
                    throw error
                }
                status = "Game folder imported and executable registered in your library."
            } else if candidates.isEmpty {
                status = "Folder copied to Wine drive_c, but no EXE was found."
            } else {
                executableCandidates = candidates.sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
                status = "Folder imported. Choose the main game EXE below."
            }
        } catch {
            executableCandidates = []
            status = "Game folder import failed: " + error.localizedDescription
        }
    }

    func selectImportedExecutable(_ executable: URL) {
        guard !busy, executableCandidates.contains(executable), executable.pathExtension.lowercased() == "exe" else { return }
        do {
            guard FileManager.default.fileExists(atPath: executable.path) else {
                status = "Executable no longer exists."
                return
            }
            try addToLibrary(executable)
            executableCandidates = []
            configExecutable = nil
            status = "Game registered. Open the Games tab to launch."
        } catch {
            status = "Could not register EXE: " + error.localizedDescription
        }
    }

    func searchSteam() async {
        let query = steamQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty, query.count <= 120, !steamBusy, !busy else { return }
        steamBusy = true
        steamGames = []
        steamError = ""
        defer { steamBusy = false }
        var parts = URLComponents(string: "https://store.steampowered.com/api/storesearch/")
        parts?.queryItems = [URLQueryItem(name: "term", value: query),
                             URLQueryItem(name: "l", value: "english"),
                             URLQueryItem(name: "cc", value: "us")]
        guard let url = parts?.url else { return }
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            steamGames = Array(try JSONDecoder().decode(AnkerSteamResponse.self, from: data).items.prefix(30))
            steamError = ""
        } catch {
            steamGames = []
            steamError = error.localizedDescription
        }
    }

    func openConfig(_ executable: URL) {
        configExecutable = executable
        let path = executable.deletingLastPathComponent().appendingPathComponent(".anker-compatibility.json")
        configText = (try? String(contentsOf: path, encoding: .utf8)) ?? """
        {"resolutionWidth":960,"resolutionHeight":540,"fpsLimit":30,"graphicsBackend":"Automatic"}
        """
        configStatus = "Edit JSON and tap Save settings."
    }

    func saveConfig() {
        guard let executable = configExecutable, executable.path.hasPrefix(LibraryModel.drive.path + "/") else {
            configStatus = "Only games on the game drive can be configured."
            return
        }
        do {
            let data = Data(configText.utf8)
            guard !data.isEmpty, data.count <= 131_072, (try JSONSerialization.jsonObject(with: data)) is [String: Any] else {
                configStatus = "Expected a JSON object."
                return
            }
            try data.write(to: executable.deletingLastPathComponent()
                .appendingPathComponent(".anker-compatibility.json"), options: .atomic)
            configStatus = "Saved locally; launch integration is pending."
        } catch { configStatus = error.localizedDescription }
    }

    func download() async {
        guard !busy, let url = validatedURL else { return }
        busy = true
        saved = nil
        downloadedBytes = 0
        expectedBytes = 0
        status = "Downloading " + url.lastPathComponent
        defer { busy = false; refresh() }
        do {
            let (temporary, response) = try await URLSession.shared.download(from: url)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                status = "The server returned an unsuccessful response."
                return
            }
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            guard (try? FileManager.default.attributesOfItem(atPath: temporary.path)[.size] as? NSNumber)?.int64Value ?? 0 > 0 else {
                status = "Downloaded file is empty."
                return
            }
            expectedBytes = response.expectedContentLength
            let candidate = response.suggestedFilename ?? url.lastPathComponent
            let name = URL(fileURLWithPath: candidate).lastPathComponent
            let safeName = name.isEmpty || name == "/" ? "download.bin" : name
            let destination = directory.appendingPathComponent(UUID().uuidString + "-" + safeName)
            try FileManager.default.moveItem(at: temporary, to: destination)
            downloadedBytes = (try? FileManager.default.attributesOfItem(atPath: destination.path)[.size] as? NSNumber)?.int64Value ?? 0
            saved = destination
            status = "Download complete"
        } catch {
            status = "Download failed (" + url.host.orEmpty + "): " + error.localizedDescription
        }
    }
}

private extension Optional where Wrapped == String {
    var orEmpty: String { self ?? "unknown host" }
}

private struct AnkerSteamResponse: Decodable {
    let items: [AnkerSteamGame]
}

private struct AnkerSteamGame: Decodable, Identifiable {
    let id: Int
    let name: String
}

struct AnkerNativeDownloads: View {
    @StateObject private var model = AnkerDownloadModel()
    @State private var selectingGameFolder = false
    @ObservedObject private var jit = JITCoordinator.shared
    @ObservedObject private var library = LibraryModel.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                runtimeHealth
                downloadCenter
                gameImport
                steamAndFiles

                Label("Downloads are saved to Documents/AnkerDownloads. EXE and extracted-folder import use your game library; archive extraction is not yet supported.",
                      systemImage: "info.circle")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 4)
            }
            .padding(18)
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .onAppear { model.refresh() }
        .fileImporter(isPresented: $selectingGameFolder,
                      allowedContentTypes: [.folder],
                      allowsMultipleSelection: false) { result in
            switch result {
            case .success(let urls):
                if let folder = urls.first { model.importGameFolder(folder) }
            case .failure(let error):
                model.status = "Folder picker failed: " + error.localizedDescription
            }
        }
    }
    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Downloads", systemImage: "arrow.down.circle.fill")
                .font(.largeTitle.bold())
            Text(String(library.entries.count) + " games in library")
                .font(.subheadline).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(24)
        .background(
            LinearGradient(colors: [.teal.opacity(0.13), .purple.opacity(0.06)],
                           startPoint: .topLeading, endPoint: .bottomTrailing),
            in: RoundedRectangle(cornerRadius: 22)
        )
    }

    private var runtimeHealth: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Runtime health", systemImage: "cpu.fill")
                .font(.headline)
            HStack {
                Text("Windows game library")
                Spacer()
                Text(String(library.entries.count) + " entries")
                    .foregroundStyle(.secondary)
            }
            HStack {
                Text("JIT method")
                Spacer()
                Text(jit.resolvedMethod.title)
                    .foregroundStyle(.secondary)
            }
            HStack {
                Text("JIT status")
                Spacer()
                Text(jit.busy ? "Connecting…" : (jit.status ?? (jit.error == nil ? "Not checked" : "Needs attention")))
                    .foregroundStyle(jit.error == nil ? Color.secondary : Color.red)
                    .lineLimit(2)
            }
            if let error = jit.error {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
            }
            if let error = library.error {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
            }
            Text("JIT status applies to your next game session.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
    }

    private var downloadCenter: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("Download center", systemImage: "arrow.down.circle.fill")
                .font(.headline)
            TextField("Paste an HTTPS game file URL", text: $model.address)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.URL)
                .textContentType(.URL)
                .submitLabel(.done)
                .padding(14)
                .background(.quaternary.opacity(0.55), in: RoundedRectangle(cornerRadius: 12))
                .accessibilityIdentifier("anker.downloads.url")
            Button {
                Task { await model.download() }
            } label: {
                HStack {
                    Spacer()
                    if model.busy { ProgressView().tint(.white) }
                    else { Image(systemName: "arrow.down.to.line.compact") }
                    Text(model.busy ? "Downloading…" : "Download file")
                        .fontWeight(.semibold)
                    Spacer()
                }
                .padding(14)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.white)
            .background(.teal, in: RoundedRectangle(cornerRadius: 13))
            .disabled(model.busy || model.validatedURL == nil)
            .opacity(model.busy || model.validatedURL == nil ? 0.55 : 1)
            .accessibilityIdentifier("anker.downloads.start")
            Text(model.status)
                .font(.footnote)
            if model.expectedBytes > 0 {
                Text("Expected: " + ByteCountFormatter.string(fromByteCount: model.expectedBytes, countStyle: .file))
                    .font(.caption).foregroundStyle(.secondary)
            }
            if model.downloadedBytes > 0 {
                Text(ByteCountFormatter.string(fromByteCount: model.downloadedBytes, countStyle: .file))
                    .font(.caption.monospacedDigit()).foregroundStyle(.secondary)
            }
            if let saved = model.saved {
                ShareLink(item: saved) {
                    Label("Share downloaded file", systemImage: "square.and.arrow.up")
                }
            }
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
    }

    private var gameImport: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Import installed game", systemImage: "folder.badge.plus")
                .font(.headline)
            Button {
                selectingGameFolder = true
            } label: {
                Label("Import extracted game folder", systemImage: "square.and.arrow.down.on.square")
            }
            .disabled(model.busy)
            if !model.executableCandidates.isEmpty {
                Text("Choose the game EXE (" + String(model.executableCandidates.count) + ")")
                    .font(.subheadline.weight(.semibold))
                ForEach(model.executableCandidates, id: \.path) { executable in
                    Button {
                        model.selectImportedExecutable(executable)
                    } label: {
                        Label(executable.lastPathComponent, systemImage: "gamecontroller.fill")
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.bordered)
                    Button("Edit settings") { model.openConfig(executable) }
                        .font(.caption)
                }
            }
            if model.configExecutable != nil {
                Text("Game settings (local JSON)").font(.headline)
                Text("Saved settings do not yet change the game launch.")
                    .font(.caption).foregroundStyle(.secondary)
                TextEditor(text: $model.configText)
                    .accessibilityIdentifier("anker.config.editor")
                    .font(.system(.caption, design: .monospaced))
                    .frame(height: 170)
                Button("Save settings") { model.saveConfig() }
                    .accessibilityIdentifier("anker.config.save")
                    .buttonStyle(.borderedProminent)
                Text(model.configStatus).font(.caption)
            }
            Text("Copies the complete folder into the Wine drive, preserving DLLs and assets.")
                .accessibilityIdentifier("anker.import.description")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
    }

    private var steamAndFiles: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 10) {
                Label("Steam lookup", systemImage: "magnifyingglass").font(.headline)
                TextField("Find a game on Steam", text: $model.steamQuery)
                    .submitLabel(.search)
                    .textFieldStyle(.roundedBorder)
                Text("Search Steam catalog by title (up to 120 characters).")
                    .font(.caption).foregroundStyle(.secondary)
                Button("Search Steam") { Task { await model.searchSteam() } }
                    .accessibilityIdentifier("anker.steam.search")
                    .disabled(model.steamBusy || model.steamQuery.isEmpty || model.steamQuery.count > 120)
                if model.steamBusy { ProgressView() }
                if !model.steamError.isEmpty {
                    Text(model.steamError).font(.caption).foregroundStyle(.red)
                }
                if !model.steamBusy && model.steamError.isEmpty && !model.steamQuery.isEmpty && model.steamGames.isEmpty {
                    Text("No Steam results loaded. Tap Search Steam.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if !model.steamGames.isEmpty {
                    Text(String(model.steamGames.count) + " Steam results")
                        .font(.caption).foregroundStyle(.secondary)
                }
                ForEach(model.steamGames) { game in
                    if let url = URL(string: "https://store.steampowered.com/app/\(game.id)/") {
                        Link(destination: url) {
                            Label(game.name, systemImage: "arrow.up.right.square")
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
            }
            Divider()
            HStack {
                Label("Downloaded files", systemImage: "folder.fill").font(.headline)
                Spacer()
                Text("\(model.files.count)")
                    .accessibilityLabel("Downloaded file count")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                Button { model.refresh() } label: { Image(systemName: "arrow.clockwise") }
            }
            if model.files.isEmpty {
                ContentUnavailableView("No downloads yet",
                                       systemImage: "tray",
                                       description: Text("Your downloaded archives and installers appear here."))
            } else {
                ForEach(model.files, id: \.path) { file in
                    HStack(spacing: 12) {
                        Image(systemName: "doc.zipper")
                            .font(.title3)
                            .foregroundStyle(.teal)
                        Text(file.lastPathComponent)
                            .font(.subheadline)
                            .lineLimit(2)
                        Spacer(minLength: 8)
                        if file.pathExtension.lowercased() == "exe" {
                            Button {
                                model.registerExecutable(file)
                            } label: {
                                Image(systemName: "plus.rectangle.on.folder")
                            }
                            .accessibilityLabel("Add executable to library")
                        }
                        ShareLink(item: file) {
                            Image(systemName: "square.and.arrow.up")
                        }
                        .accessibilityLabel("Share " + file.lastPathComponent)
                    }
                    .padding(.vertical, 7)
                    Divider()
                }
            }
        }
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
    }
}
'''
assets = Path(__file__).resolve().parents[1] / "ui"
original += "\n" + (assets / "AnkerWorkspace.swift").read_text()
library = source.with_name("Library.swift")
if library.exists():
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("workspace_overlay", assets / "workspace_overlay.py")
    overlay = module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.install(source.parent)
source.write_text(original)
print("Added Anker Downloads to the real Madeira application entry point.")
