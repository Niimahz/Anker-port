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
    static let shared = AnkerDownloadModel()
    @Published var extracting: Set<URL> = []
    private var queue: [URL] = []
    @Published var extractionErrors: [URL: String] = [:]
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
        let input = address.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !input.isEmpty, !input.contains(where: { $0.isWhitespace }) else { return nil }
        let candidate = URLComponents(string: input)?.scheme == nil ? "https://" + input : input
        guard let url = URL(string: candidate),
              let scheme = url.scheme?.lowercased(),
              scheme == "https",
              url.host != nil, url.user == nil, url.password == nil else { return nil }
        return url
    }

    func refresh() {
        files = (try? FileManager.default.contentsOfDirectory(
            at: directory, includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]))?
            .filter { $0.isFileURL }
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending } ?? []
    }

    func isArchive(_ url: URL) -> Bool {
        if url.hasDirectoryPath { return false }
        if ["zip", "rar", "7z", "tar", "gz", "tgz"].contains(url.pathExtension.lowercased()) { return true }
        guard let handle = try? FileHandle(forReadingFrom: url) else { return false }
        defer { try? handle.close() }
        let prefix = Array((try? handle.read(upToCount: 512)) ?? Data())
        return prefix.starts(with: [0x1f, 0x8b, 8]) ||
            prefix.dropFirst(257).starts(with: "ustar".utf8) ||
            prefix.starts(with: [0x50, 0x4b, 3, 4]) ||
            prefix.starts(with: [0x52, 0x61, 0x72, 0x21]) ||
            prefix.starts(with: [0x37, 0x7a, 0xbc, 0xaf, 0x27, 0x1c])
    }

    func didSave(_ file: URL) {
        refresh()
        if isArchive(file) { extract(file) }
    }

    func extract(_ file: URL) {
        guard files.contains(file), !extracting.contains(file) else { return }
        extractionErrors[file] = nil
        extracting.insert(file)
        queue.append(file)
        if extracting.count == 1 { Task { await drainQueue() } }
    }

    private func drainQueue() async {
        while !queue.isEmpty {
            let file = queue.removeFirst()
            let destination = directory.appendingPathComponent(file.lastPathComponent + ".extracted", isDirectory: true)
            do {
                try await Task.detached(priority: .utility) {
                    let fm = FileManager.default
                    guard !fm.fileExists(atPath: destination.path) else {
                        throw NSError(domain: "AnkerArchive", code: 1, userInfo: [NSLocalizedDescriptionKey: "The extracted folder already exists."])
                    }
                    let stage = file.deletingLastPathComponent().appendingPathComponent(".extract-" + UUID().uuidString)
                    try fm.createDirectory(at: stage, withIntermediateDirectories: false)
                    defer { try? fm.removeItem(at: stage) }
                    var message = [CChar](repeating: 0, count: 512)
                    guard anker_unpack(file.path, stage.path, &message, 512) == 0 else {
                        throw NSError(domain: "AnkerArchive", code: 2, userInfo: [NSLocalizedDescriptionKey: String(cString: message)])
                    }
                    try fm.moveItem(at: stage, to: destination)
                }.value
                status = "Extraction complete"
            } catch {
                extractionErrors[file] = error.localizedDescription
                status = "Extraction failed: " + error.localizedDescription
            }
            extracting.remove(file)
            refresh()
        }
    }

    func deleteDownload(_ file: URL) {
        guard files.contains(file), !extracting.contains(file) else { return }
        do {
            try FileManager.default.removeItem(at: file)
            if saved == file { saved = nil }
            extractionErrors[file] = nil
            refresh()
        } catch { status = "Delete failed: " + error.localizedDescription }
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
            // A Windows EXE often depends on DLLs and assets beside it.
            // Import its containing directory, not the EXE alone.
            let sourceFolder = file.deletingLastPathComponent()
            var traversalError: Error?
            guard let walker = FileManager.default.enumerator(
                at: sourceFolder, includingPropertiesForKeys: [.isSymbolicLinkKey],
                options: [], errorHandler: { _, error in
                    traversalError = error
                    return false
                }) else {
                throw NSError(domain: "AnkerImport", code: 2, userInfo: [
                    NSLocalizedDescriptionKey: "Cannot inspect the executable's game folder."
                ])
            }
            while let item = walker.nextObject() as? URL {
                let values = try item.resourceValues(forKeys: [.isSymbolicLinkKey])
                guard values.isSymbolicLink != true else {
                    throw NSError(domain: "AnkerImport", code: 3, userInfo: [
                        NSLocalizedDescriptionKey: "Game folder contains a symbolic link; import cancelled."
                    ])
                }
            }
            if let traversalError { throw traversalError }
            let destination = targetFolder.appendingPathComponent(
                UUID().uuidString + "-" + sourceFolder.lastPathComponent, isDirectory: true)
            try FileManager.default.copyItem(at: sourceFolder, to: destination)
            let target = destination.appendingPathComponent(file.lastPathComponent)
            do {
                try addToLibrary(target)
                status = "Game folder and executable added to your library."
            } catch {
                try? FileManager.default.removeItem(at: destination)
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
            // Reject links before copying: a linked asset could escape the selected
            // game tree, while Wine expects a self-contained drive_c directory.
            var traversalError: Error?
            guard let preflight = FileManager.default.enumerator(
                at: source, includingPropertiesForKeys: [.isSymbolicLinkKey],
                options: [], errorHandler: { _, error in
                    traversalError = error
                    return false
                }) else {
                status = "Cannot inspect the selected game folder."
                return
            }
            var containsExecutable = false
            while let item = preflight.nextObject() as? URL {
                let values = try item.resourceValues(forKeys: [.isSymbolicLinkKey, .isRegularFileKey])
                guard values.isSymbolicLink != true else {
                    status = "Game folder contains a symbolic link; import cancelled."
                    return
                }
                if values.isRegularFile == true && item.pathExtension.lowercased() == "exe" {
                    containsExecutable = true
                }
            }
            if let traversalError {
                status = "Cannot read the complete game folder: " + traversalError.localizedDescription
                return
            }
            guard containsExecutable else {
                status = "No Windows EXE found; nothing was copied."
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
            let configuration = URLSessionConfiguration.ephemeral
            let cookies = await WKWebsiteDataStore.default().httpCookieStore.allCookies()
            for cookie in cookies { configuration.httpCookieStorage?.setCookie(cookie) }
            let session = URLSession(configuration: configuration)
            defer { session.finishTasksAndInvalidate() }
            let (temporary, response) = try await session.download(from: url)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                status = "Download failed. HTTP " + String((response as? HTTPURLResponse)?.statusCode ?? 0)
                return
            }
            if ["text/html", "application/xhtml+xml"].contains(response.mimeType?.lowercased() ?? "") {
                status = "This link opened a webpage. Open it in Browser and tap the site’s download button."
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
            didSave(destination)
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
    @ObservedObject private var model = AnkerDownloadModel.shared
    private enum Pane: String, CaseIterable { case files = "Files", tools = "Game tools" }
    @Namespace private var paneSelection
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pane = Pane.files
    @State private var pendingDelete: URL?
    @State private var selectingGameFolder = false
    @ObservedObject private var jit = JITCoordinator.shared
    @ObservedObject private var library = LibraryModel.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                HStack(spacing: 4) {
                    ForEach(Pane.allCases, id: \.self) { option in
                        Button {
                            withAnimation(reduceMotion ? nil : .spring(duration: 0.3)) { pane = option }
                        } label: {
                            Label(option.rawValue, systemImage: option == .files ? "tray.full" : "wrench.and.screwdriver")
                                .font(.subheadline.weight(.semibold)).frame(maxWidth: .infinity, minHeight: 44)
                                .foregroundStyle(option == pane ? Color.black : Color.primary)
                                .background {
                                    if pane == option {
                                        Capsule().fill(PortStyle.signal).matchedGeometryEffect(id: "pane", in: paneSelection)
                                    }
                                }
                        }.buttonStyle(PortPress()).accessibilityAddTraits(option == pane ? .isSelected : [])
                    }
                }.padding(4).background(PortStyle.panel, in: Capsule())
                if pane == .files {
                    downloadCenter
                    downloadsList
                } else {
                    gameImport
                    steamLookup
                    runtimeHealth
                }
            }
            .padding(18)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(PortStyle.ground)
        .onAppear { model.refresh() }
        .alert("Delete download?", isPresented: Binding(get: { pendingDelete != nil }, set: { if !$0 { pendingDelete = nil } }), presenting: pendingDelete) { url in
            Button("Delete", role: .destructive) { model.deleteDownload(url) }
            Button("Cancel", role: .cancel) {}
        } message: { url in Text(displayName(url)) }
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
        HStack {
            Text("Downloads").font(.system(.largeTitle, design: .rounded, weight: .heavy))
            Spacer()
            Text(String(model.files.count)).font(.title3.monospacedDigit().bold())
                .foregroundStyle(PortStyle.accent)
                .accessibilityLabel("Downloaded files: " + String(model.files.count))
        }
    }

    // A user-initiated, copyable diagnostic snapshot. Never include URLs, file paths,
    // download cookies or executable arguments in the shared report.
    // Export only an error category: upstream error text can contain local paths.
    private var ankerJITErrorCategory: String {
        guard let error = jit.error, !error.isEmpty else { return "None reported" }
        let normalized = error.lowercased()
        if normalized.contains("timeout") || normalized.contains("timed out") { return "Timeout" }
        if normalized.contains("permission") || normalized.contains("denied") { return "Permission denied" }
        if normalized.contains("connect") || normalized.contains("network") { return "Connection problem" }
        if normalized.contains("unsupported") || normalized.contains("unavailable") { return "Unavailable method" }
        return "Unclassified error (details remain on device)"
    }

    // The upstream library error may include absolute paths and game names.
    // Keep the shared report categorical; full details remain on the device.
    private var ankerLibraryErrorCategory: String {
        guard let error = library.error, !error.isEmpty else { return "None reported" }
        let normalized = error.lowercased()
        if normalized.contains("permission") || normalized.contains("denied") { return "Permission denied" }
        if normalized.contains("not found") || normalized.contains("missing") || normalized.contains("no such file") { return "Missing file" }
        if normalized.contains("space") || normalized.contains("storage") || normalized.contains("disk full") { return "Storage problem" }
        if normalized.contains("invalid") || normalized.contains("unsupported") || normalized.contains("format") { return "Invalid or unsupported executable" }
        return "Unclassified error (details remain on device)"
    }

    private var ankerRuntimeDiagnostic: String {
        let jitState = jit.busy ? "Connecting" : (jit.status ?? "Not checked")
        return [
            "Anker Port runtime diagnostic",
            "Generated: \(Date().formatted(.iso8601))",
            "Library entries: \(library.entries.count)",
            "JIT method: \(jit.resolvedMethod.title)",
            "JIT state: \(jitState)",
            "JIT error category: \(ankerJITErrorCategory)",
            "JIT execution verified: No (status snapshot only)",
            "Library error: \(ankerLibraryErrorCategory)",
            "Note: This is a status snapshot, not proof that an EXE launched."
        ].joined(separator: "\n")
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
            ShareLink(item: ankerRuntimeDiagnostic) {
                Label("Share runtime diagnostic", systemImage: "square.and.arrow.up")
            }
            .accessibilityIdentifier("anker.runtime.share-diagnostic")
            Text("JIT status applies to your next game session.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(18)
        .portPanel()
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
                .submitLabel(.go)
                .onSubmit { Task { await model.download() } }
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
            .background(Color(red: 0.66, green: 0.22, blue: 0.055), in: RoundedRectangle(cornerRadius: 13))
            .disabled(model.busy || model.validatedURL == nil)
            .opacity(model.busy || model.validatedURL == nil ? 0.55 : 1)
            .accessibilityIdentifier("anker.downloads.start")
            if model.busy {
                PortActivity(label: model.status)
            } else {
                Text(model.status).font(.footnote)
            }
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
        .portPanel()
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
        .portPanel()
    }

    private var steamLookup: some View {
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
            .padding(18)
            .portPanel()
    }

    private func displayName(_ file: URL) -> String {
        let name = file.lastPathComponent
        guard name.count > 37, UUID(uuidString: String(name.prefix(36))) != nil,
              name.dropFirst(36).first == "-" else { return name }
        return String(name.dropFirst(37))
    }

    private var downloadsList: some View {
        VStack(alignment: .leading, spacing: 12) {
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
                        Image(systemName: file.hasDirectoryPath ? "folder.fill" : "doc.zipper")
                            .font(.title3)
                            .foregroundStyle(PortStyle.accent)
                        Text(displayName(file))
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
                    HStack {
                        if file.hasDirectoryPath {
                            Button("Import game") { model.importGameFolder(file) }
                        } else if model.isArchive(file) {
                            if model.extracting.contains(file) {
                                PortActivity(label: "Extracting…")
                            } else {
                                Button { model.extract(file) } label: {
                                    Label("Extract", systemImage: "shippingbox")
                                }.buttonStyle(.bordered)
                            }
                        }
                        Spacer()
                        Button("Delete", role: .destructive) { pendingDelete = file }
                            .disabled(model.extracting.contains(file))
                    }
                    if let error = model.extractionErrors[file] {
                        Text(error).font(.caption).foregroundStyle(.red)
                    }
                    Divider()
                }
            }
        }
        .padding(18)
        .portPanel()
    }
}
'''
assets = Path(__file__).resolve().parents[1] / "ui"
original += "\n" + (assets / "AnkerWorkspace.swift").read_text()
original += "\n" + (assets / "PortGameExport.swift").read_text()
library = source.with_name("Library.swift")
if library.exists():
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("workspace_overlay", assets / "workspace_overlay.py")
    overlay = module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.install(source.parent)
source.write_text(original)
print("Added Anker Downloads to the real Madeira application entry point.")
