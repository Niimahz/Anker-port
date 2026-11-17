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
original = original.replace(marker, """            ContentView()
                .overlay(alignment: .topTrailing) {
                    AnkerDownloadEntry()
                        .padding(.top, 8)
                        .padding(.trailing, 12)
                }
""", 1)
original += r'''
// ANKER_PORT_INTEGRATION_V1
// Additive SwiftUI experience: upstream Madeira library and Wine launch stay untouched.
private struct AnkerDownloadEntry: View {
    @State private var showingHub = false

    var body: some View {
        Button { showingHub = true } label: {
            Label("Anker", systemImage: "square.stack.3d.up.fill")
                .font(.subheadline.weight(.bold))
                .padding(.horizontal, 15)
                .padding(.vertical, 10)
                .foregroundStyle(.white)
                .background(
                    LinearGradient(colors: [Color(red: 0.20, green: 0.37, blue: 0.96),
                                            Color(red: 0.42, green: 0.25, blue: 0.84)],
                                   startPoint: .topLeading, endPoint: .bottomTrailing),
                    in: Capsule()
                )
                .shadow(color: .indigo.opacity(0.25), radius: 9, y: 4)
        }
        .accessibilityIdentifier("anker.downloads.open")
        .sheet(isPresented: $showingHub) {
            NavigationStack { AnkerNativeDownloads() }
                .tint(.indigo)
        }
    }
}

@MainActor
private final class AnkerDownloadModel: ObservableObject {
    @Published var address = ""
    @Published var status = "Ready to download"
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
              ["http", "https"].contains(scheme),
              url.host != nil else { return nil }
        return url
    }

    func refresh() {
        files = (try? FileManager.default.contentsOfDirectory(
            at: directory, includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]))?
            .filter { $0.isFileURL && !$0.hasDirectoryPath }
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending } ?? []
    }

    // Reuse Madeira's PE inspector and native library persistence.
    func registerExecutable(_ file: URL) {
        guard !busy else { return }
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
                LibraryModel.shared.save(try LibraryModel.inspect(target))
                status = "Added to Madeira library. Launch it from the Games tab."
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
                    if file.pathExtension.lowercased() == "exe" {
                        candidates.append(file)
                        if candidates.count > 500 { break }
                    }
                }
            }
            if candidates.count == 1, let executable = candidates.first {
                LibraryModel.shared.save(try LibraryModel.inspect(executable))
                status = "Game folder imported and executable registered in Madeira."
            } else if candidates.isEmpty {
                status = "Folder copied to Wine drive_c, but no EXE was found."
            } else {
                executableCandidates = candidates.sorted { $0.lastPathComponent < $1.lastPathComponent }
                status = "Folder imported. Choose the main game EXE below."
            }
        } catch {
            status = "Game folder import failed: " + error.localizedDescription
        }
    }

    func selectImportedExecutable(_ executable: URL) {
        guard !busy, executableCandidates.contains(executable) else { return }
        do {
            LibraryModel.shared.save(try LibraryModel.inspect(executable))
            executableCandidates = []
            status = "Game registered. Open the Games tab to launch."
        } catch {
            status = "Could not register EXE: " + error.localizedDescription
        }
    }

    func searchSteam() async {
        let query = steamQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty, !steamBusy else { return }
        steamBusy = true
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
            steamGames = try JSONDecoder().decode(AnkerSteamResponse.self, from: data).items
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
        configStatus = ""
    }

    func saveConfig() {
        guard let executable = configExecutable else { return }
        do {
            let data = Data(configText.utf8)
            guard (try JSONSerialization.jsonObject(with: data)) is [String: Any] else {
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
            let candidate = response.suggestedFilename ?? url.lastPathComponent
            let name = URL(fileURLWithPath: candidate).lastPathComponent
            let safeName = name.isEmpty || name == "/" ? "download.bin" : name
            let destination = directory.appendingPathComponent(UUID().uuidString + "-" + safeName)
            try FileManager.default.moveItem(at: temporary, to: destination)
            saved = destination
            status = "Download complete"
        } catch {
            status = "Download failed: " + error.localizedDescription
        }
    }
}

private struct AnkerSteamResponse: Decodable {
    let items: [AnkerSteamGame]
}

private struct AnkerSteamGame: Decodable, Identifiable {
    let id: Int
    let name: String
}

private struct AnkerNativeDownloads: View {
    @StateObject private var model = AnkerDownloadModel()
    @State private var selectingGameFolder = false
    @ObservedObject private var jit = JITCoordinator.shared
    @ObservedObject private var library = LibraryModel.shared
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                VStack(alignment: .leading, spacing: 8) {
                    Label("ANKER PORT", systemImage: "square.stack.3d.up.fill")
                        .font(.caption.weight(.heavy))
                        .tracking(2)
                        .foregroundStyle(.indigo)
                    Text("Your Windows gaming hub.")
                        .font(.system(size: 32, weight: .heavy, design: .rounded))
                        .minimumScaleFactor(0.75)
                    Text("Download, import and organize games. Powered by the Madeira runtime.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(24)
                .background(
                    LinearGradient(colors: [.indigo.opacity(0.13), .purple.opacity(0.06)],
                                   startPoint: .topLeading, endPoint: .bottomTrailing),
                    in: RoundedRectangle(cornerRadius: 22)
                )

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
                            .foregroundStyle(jit.error == nil ? .secondary : .red)
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
                    Text("Game launches and JIT activation remain managed by Madeira.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(18)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))

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
                    .background(.indigo, in: RoundedRectangle(cornerRadius: 13))
                    .disabled(model.busy || model.validatedURL == nil)
                    .opacity(model.busy || model.validatedURL == nil ? 0.55 : 1)
                    .accessibilityIdentifier("anker.downloads.start")
                    Text(model.status)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    if let saved = model.saved {
                        ShareLink(item: saved) {
                            Label("Share downloaded file", systemImage: "square.and.arrow.up")
                        }
                    }
                }
                .padding(18)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))

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
                        Text("Choose the game EXE").font(.subheadline.weight(.semibold))
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
                        Text("Game settings").font(.headline)
                        TextEditor(text: $model.configText)
                            .font(.system(.caption, design: .monospaced))
                            .frame(height: 170)
                        Button("Save settings") { model.saveConfig() }
                            .buttonStyle(.borderedProminent)
                        Text(model.configStatus).font(.caption)
                    }
                    Text("Copies the complete folder into Madeira's Wine drive, preserving DLLs and assets.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(18)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))

                VStack(alignment: .leading, spacing: 12) {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Steam lookup", systemImage: "magnifyingglass").font(.headline)
                        TextField("Find a game on Steam", text: $model.steamQuery)
                            .textFieldStyle(.roundedBorder)
                        Button("Search Steam") { Task { await model.searchSteam() } }
                            .disabled(model.steamBusy || model.steamQuery.isEmpty)
                        if model.steamBusy { ProgressView() }
                        if !model.steamError.isEmpty {
                            Text(model.steamError).font(.caption).foregroundStyle(.red)
                        }
                        ForEach(model.steamGames) { game in
                            if let url = URL(string: "https://store.steampowered.com/app/\(game.id)/") {
                                Link(game.name, destination: url)
                            }
                        }
                    }
                    Divider()
                    HStack {
                        Label("Downloaded files", systemImage: "folder.fill").font(.headline)
                        Spacer()
                        Text("\(model.files.count)")
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
                                    .foregroundStyle(.indigo)
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
                                    .accessibilityLabel("Add executable to Madeira library")
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

                Label("Downloads are saved to Documents/AnkerDownloads. EXE and extracted-folder import use Madeira's native library; archive extraction is not yet supported.",
                      systemImage: "info.circle")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 4)
            }
            .padding(18)
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Anker Port")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Done") { dismiss() }
            }
        }
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
}
'''
source.write_text(original)
print("Added Anker Downloads to the real Madeira application entry point.")
