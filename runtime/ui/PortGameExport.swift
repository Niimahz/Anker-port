import Darwin
import WebKit
import UniformTypeIdentifiers

// Appended to the native target alongside the Anker workspace.
private struct PortGamePackageError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

enum PortGamePackage {
    static var seed: URL { Bundle.main.bundleURL.appendingPathComponent("PortSeed.bin") }
    static var profile: URL { Bundle.main.bundleURL.appendingPathComponent("PortGame.json") }
    static var standalone: Bool { FileManager.default.fileExists(atPath: profile.path) }

    static func savedIPA(_ id: UUID, jitless: Bool, legacy: Bool = false) -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent(legacy ? "AnkerExports" : "Anker IPA", isDirectory: true)
            .appendingPathComponent("Game-" + id.uuidString + (jitless ? "-JITless.ipa" : "-WithJIT.ipa"))
    }

    static func importedRoot(_ entry: LibraryEntry) -> URL? {
        let parts = entry.relativePath.split(separator: "/")
        guard parts.count >= 4, parts[0] == "Games", parts[1] == "AnkerImports",
              UUID(uuidString: String(parts[2].prefix(36))) != nil else { return nil }
        return LibraryModel.drive.appendingPathComponent(parts.prefix(3).joined(separator: "/"), isDirectory: true)
    }

    static func webIndex(for executable: URL, inside root: URL) -> URL? {
        let base = executable.deletingLastPathComponent()
        let source = root.resolvingSymlinksInPath().standardizedFileURL.path + "/"
        for directory in [base.appendingPathComponent("www"), base] {
            func has(_ path: String) -> Bool {
                let file = directory.appendingPathComponent(path).resolvingSymlinksInPath().standardizedFileURL
                return file.path.hasPrefix(source) &&
                    (try? file.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true
            }
            if has("index.html"), has("js/main.js"), has("data/System.json"),
               has("js/rpg_core.js") || has("js/rmmz_core.js") {
                return directory.appendingPathComponent("index.html").resolvingSymlinksInPath().standardizedFileURL
            }
        }
        return nil
    }

    static func isWin32Game(_ url: URL) -> Bool {
        guard let file = try? FileHandle(forReadingFrom: url) else { return false }
        defer { try? file.close() }
        do {
            guard let dos = try file.read(upToCount: 64), dos.count == 64,
                  dos.starts(with: [0x4d, 0x5a]) else { return false }
            let offset = dos[60..<64].enumerated().reduce(UInt64(0)) {
                $0 | (UInt64($1.element) << (8 * $1.offset))
            }
            guard offset >= 64 else { return false }
            try file.seek(toOffset: offset)
            guard let pe = try file.read(upToCount: 26), pe.count == 26 else { return false }
            return pe.starts(with: [0x50, 0x45, 0, 0, 0x4c, 0x01]) &&
                pe[22] & 2 != 0 && pe[23] & 0x20 == 0 && pe[24] == 0x0b && pe[25] == 1
        } catch { return false }
    }

    static func export(_ entry: LibraryEntry, root: URL, executable: URL, jitless: Bool) throws -> URL {
        let fm = FileManager.default
        let source = root.resolvingSymlinksInPath().standardizedFileURL
        let exe = executable.resolvingSymlinksInPath().standardizedFileURL
        let drive = LibraryModel.drive.resolvingSymlinksInPath().standardizedFileURL
        guard source != drive, source.path != drive.path,
              !drive.path.hasPrefix(source.path + "/"), exe.path.hasPrefix(source.path + "/"),
              exe.pathExtension.lowercased() == "exe", fm.fileExists(atPath: exe.path) else {
            throw PortGamePackageError("Select the individual game folder containing this EXE and its assets.")
        }
        let index = jitless ? webIndex(for: exe, inside: source) : nil
        let useBoxedWine = jitless && index == nil
        if useBoxedWine && !isWin32Game(exe) {
            throw PortGamePackageError("JITless needs a 32-bit x86 Windows EXE or RPG Maker MV/MZ browser assets.")
        }
        let seedInfo = try Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("PortSeed.plist"))
        guard let metadata = try PropertyListSerialization.propertyList(from: seedInfo, format: nil) as? [String: Any],
              var info = metadata["info"] as? [String: Any], let prefix = metadata["prefix"] as? String else {
            throw PortGamePackageError("The export template is incomplete.")
        }
        let temp = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try fm.createDirectory(at: temp, withIntermediateDirectories: true)
        let destination = savedIPA(entry.id, jitless: jitless)
        let exported = temp.appendingPathComponent(destination.lastPathComponent)
        do {
            info["CFBundleIdentifier"] = "app.ankerport.game.g" + entry.id.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
            if let index {
                info["AnkerWebIndex"] = String(index.path.dropFirst(source.path.count + 1))
                info["CFBundleIdentifier"] = "app.ankerport.game.web.g" + entry.id.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
            }
            if useBoxedWine {
                info["AnkerBoxedExecutable"] = String(exe.path.dropFirst(source.path.count + 1))
                info["CFBundleIdentifier"] = "app.ankerport.game.win32.g" + entry.id.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
            }
            info["CFBundleDisplayName"] = entry.title
            info["CFBundleName"] = entry.title
            let plist = temp.appendingPathComponent("Info.plist")
            try PropertyListSerialization.data(fromPropertyList: info, format: .binary, options: 0).write(to: plist)
            var game = entry
            game.coverFile = nil
            game.relativePath = "Games/AnkerStandalone/" + entry.id.uuidString + "/" + String(exe.path.dropFirst(source.path.count + 1))
            if let dir = game.workingDirectory, dir.lowercased().hasPrefix("c:\\") {
                let path = String(dir.dropFirst(3)).replacingOccurrences(of: "\\", with: "/")
                let actual = drive.appendingPathComponent(path).resolvingSymlinksInPath().standardizedFileURL.path
                guard actual == source.path || actual.hasPrefix(source.path + "/") || jitless else {
                    throw PortGamePackageError("The launch folder is outside this game package. Select a common game folder or change the working directory before exporting.")
                }
                if actual == source.path || actual.hasPrefix(source.path + "/") {
                    game.workingDirectory = "C:\\Games\\AnkerStandalone\\" + entry.id.uuidString + String(actual.dropFirst(source.path.count)).replacingOccurrences(of: "/", with: "\\")
                }
            }
            let manifest = temp.appendingPathComponent("PortGame.json")
            try JSONEncoder().encode(game).write(to: manifest)
            var error = [CChar](repeating: 0, count: 512)
            var payload = source
            if useBoxedWine {
                payload = temp.appendingPathComponent("Win32", isDirectory: true)
                try fm.createDirectory(at: payload, withIntermediateDirectories: true)
                let zip = payload.appendingPathComponent("game.zip")
                guard port_build_ipa(nil, "", source.path, nil, nil, zip.path, &error, 512) == 0 else {
                    throw PortGamePackageError(String(cString: error))
                }
            }
            guard port_build_ipa(seed.path, prefix, payload.path, plist.path, manifest.path, exported.path, &error, 512) == 0 else {
                throw PortGamePackageError(String(cString: error))
            }
            try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
            // Publish only the completed file, atomically replacing the previous export of this mode.
            guard rename(exported.path, destination.path) == 0 else {
                throw NSError(domain: NSPOSIXErrorDomain, code: Int(errno))
            }
            try? fm.removeItem(at: temp)
            return destination
        } catch {
            try? fm.removeItem(at: temp)
            throw error
        }
    }

    static func install() throws -> LibraryEntry {
        let fm = FileManager.default
        let game = try JSONDecoder().decode(LibraryEntry.self, from: Data(contentsOf: profile))
        let relativeRoot = "Games/AnkerStandalone/" + game.id.uuidString
        guard game.relativePath.hasPrefix(relativeRoot + "/"),
              !game.relativePath.split(separator: "/").contains("..") else {
            throw PortGamePackageError("Invalid game manifest.")
        }
        let target = LibraryModel.drive.appendingPathComponent(relativeRoot, isDirectory: true)
        let parent = target.deletingLastPathComponent()
        if !fm.fileExists(atPath: target.path) {
            try fm.createDirectory(at: parent, withIntermediateDirectories: true)
            let stage = parent.appendingPathComponent(".install-" + UUID().uuidString, isDirectory: true)
            defer { try? fm.removeItem(at: stage) }
            try fm.copyItem(at: Bundle.main.bundleURL.appendingPathComponent("PortGameFiles"), to: stage)
            let exe = stage.appendingPathComponent(String(game.relativePath.dropFirst(relativeRoot.count + 1)))
            guard fm.fileExists(atPath: exe.path) else { throw PortGamePackageError("Game executable missing from package.") }
            try fm.moveItem(at: stage, to: target)
        }
        _ = try LibraryModel.executable(game.relativePath)
        return game
    }
}

// Give the game's scripts a single origin and access only to their own assets.
private final class PortWebAssets: NSObject, WKURLSchemeHandler {
    let directory: URL
    let gameArchive: URL?
    init(directory: URL, gameArchive: URL?) {
        self.directory = directory.resolvingSymlinksInPath().standardizedFileURL
        self.gameArchive = gameArchive
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, url.host == "game" else {
            task.didFailWithError(URLError(.badURL))
            return
        }
        let asset = directory.appendingPathComponent(url.path).resolvingSymlinksInPath().standardizedFileURL
        guard asset.path.hasPrefix(directory.path + "/") else {
            task.didFailWithError(URLError(.noPermissionsToReadFile))
            return
        }
        let file = url.path == "/game.zip" ? (gameArchive ?? asset) : asset
        do {
            let bytes = try Data(contentsOf: file, options: .mappedIfSafe)
            let mime = UTType(filenameExtension: file.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
            // BrowserFS accepts archive reads only when XHR reports HTTP 200.
            guard let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": mime, "Content-Length": String(bytes.count)]) else {
                throw URLError(.badServerResponse)
            }
            task.didReceive(response)
            task.didReceive(bytes)
            task.didFinish()
        } catch { task.didFailWithError(error) }
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}

// The native Metal surface sits above SwiftUI. Pin the tag to the actual
// rendering view in both engines so it follows rotation and stays touch-transparent.
@MainActor
private final class PortGameWatermark: UILabel {
    static func attach(to surface: UIView) {
        guard PortGamePackage.standalone,
              !surface.subviews.contains(where: { $0 is PortGameWatermark }) else { return }
        let label = PortGameWatermark(frame: .zero)
        label.text = "Anker Port"
        label.font = .systemFont(ofSize: 10, weight: .semibold)
        label.textColor = UIColor.white.withAlphaComponent(0.65)
        label.shadowColor = UIColor.black.withAlphaComponent(0.75)
        label.shadowOffset = CGSize(width: 0, height: 1)
        label.isUserInteractionEnabled = false
        label.isAccessibilityElement = false
        label.translatesAutoresizingMaskIntoConstraints = false
        surface.addSubview(label)
        let safe = surface.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            label.trailingAnchor.constraint(equalTo: safe.trailingAnchor, constant: -10),
            label.bottomAnchor.constraint(equalTo: safe.bottomAnchor, constant: -5)
        ])
    }
}

private struct PortWebGame: UIViewRepresentable {
    let directory: URL

    var boxedExecutable: String? = nil

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        var gameArchive: URL?
        if let boxedExecutable, let data = try? JSONEncoder().encode(boxedExecutable),
           let literal = String(data: data, encoding: .utf8) {
            gameArchive = Bundle.main.bundleURL.appendingPathComponent("PortGameFiles/game.zip")
            configuration.userContentController.addUserScript(WKUserScript(
                source: "window.ankerExecutable = " + literal,
                injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
        configuration.setURLSchemeHandler(PortWebAssets(directory: directory, gameArchive: gameArchive), forURLScheme: "ankergame")
        let view = WKWebView(frame: .zero, configuration: configuration)
        PortGameWatermark.attach(to: view)
        view.load(URLRequest(url: URL(string: "ankergame://game/index.html")!))
        return view
    }

    func updateUIView(_ view: WKWebView, context: Context) {}
}

struct PortSingleGame: View {
    let play: (LibraryEntry) -> Void
    @ObservedObject private var model = LibraryModel.shared
    @State private var ready: LibraryEntry?
    @State private var failure: String?
    @State private var loading = false
    var body: some View {
        if let executable = Bundle.main.object(forInfoDictionaryKey: "AnkerBoxedExecutable") as? String {
            PortWebGame(directory: Bundle.main.bundleURL.appendingPathComponent("PortBoxedWine"), boxedExecutable: executable)
        } else if let index = Bundle.main.object(forInfoDictionaryKey: "AnkerWebIndex") as? String {
            let root = Bundle.main.bundleURL.appendingPathComponent("PortGameFiles")
            let page = root.appendingPathComponent(index).standardizedFileURL
            if page.path.hasPrefix(root.path + "/"), FileManager.default.fileExists(atPath: page.path) {
                PortWebGame(directory: page.deletingLastPathComponent())
            } else {
                Text("The packaged game is missing its web entry point.")
            }
        } else {
            windowsLauncher
        }
    }

    private var windowsLauncher: some View {
        VStack(spacing: 18) {
            PortMark().frame(width: 70, height: 60)
            Text(Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String ?? "Game").font(.largeTitle.bold())
            if loading { ProgressView("Preparing game files…") }
            if let error = failure ?? model.error { Text(error).font(.footnote).foregroundStyle(.secondary) }
            if let ready { Button("Play") { model.error = nil; PortGameWatermark.attach(to: MetalHostView.shared); play(ready) }.buttonStyle(.borderedProminent) }
            else if failure != nil { Button("Retry") { Task { await prepare() } } }
        }.padding().task { if ready == nil && failure == nil { await prepare() } }
    }
    @MainActor private func prepare() async {
        guard !loading else { return }
        failure = nil; loading = true
        defer { loading = false }
        do {
            let bundled = try await Task.detached(priority: .userInitiated) { try PortGamePackage.install() }.value
            if let existing = model.entries.first(where: { $0.id == bundled.id }) { ready = existing }
            else { model.save(bundled); ready = bundled }
        } catch { failure = error.localizedDescription }
    }
}

struct PortExportSection: View {
    let entry: LibraryEntry
    @State private var choose = false
    @State private var confirm = false
    @State private var supportsWeb = false
    @State private var supportsWin32 = false
    @State private var folder: URL?
    @State private var busy = false
    @State private var message = ""
    @State private var files: [URL] = []
    @State private var removal: URL?
    @State private var confirmRemoval = false

    var body: some View {
        if !PortGamePackage.standalone && entry.relativePath.lowercased().hasSuffix(".exe") && entry.desktop != true {
            Section {
                Button {
                    if let root = PortGamePackage.importedRoot(entry) { select(root) }
                    else { choose = true }
                } label: { Label("Export game IPA", systemImage: "shippingbox") }.disabled(busy)
                if busy { ProgressView("Packaging runtime and game files…") }
                ForEach(files, id: \.self) { file in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(file.lastPathComponent.hasSuffix("-JITless.ipa") ? "JITless IPA" : "With JIT IPA")
                        HStack {
                            Text(file.deletingLastPathComponent().lastPathComponent + "/" + file.lastPathComponent).font(.caption).textSelection(.enabled)
                            Spacer()
                            Button("Remove", role: .destructive) { removal = file; confirmRemoval = true }
                        }.buttonStyle(.borderless)
                    }.disabled(busy)
                }
                if !message.isEmpty { Text(message).font(.footnote) }
            } footer: { Text("Includes the selected game folder and runtime for use on another device without Anker Port. Choose With JIT for 32-bit x86 and 64-bit x64 Windows EXEs or JITless for RPG Maker web games and experimental 32-bit Windows emulation. Store clients and system-wide dependencies may need separate setup.") }
            .fileImporter(isPresented: $choose, allowedContentTypes: [.folder]) { value in
                do { select(try value.get()) } catch { message = error.localizedDescription }
            }
            .confirmationDialog("Export game IPA", isPresented: $confirm, titleVisibility: .visible) {
                Button("With JIT · x86 / x64") { if let folder { Task { await build(folder, jitless: false) } } }
                Button(supportsWeb ? "JITless · RPG Maker Web" : "JITless · Win32 (Experimental)") { if let folder { Task { await build(folder, jitless: true) } } }.disabled(!supportsWeb && !supportsWin32)
                Button("Cancel", role: .cancel) {}
            } message: { Text("Includes the entire game folder. " + (supportsWeb ? "Browser assets detected. Windows-only plugins may be incompatible." : (supportsWin32 ? "32-bit x86 EXE detected. Older lightweight games are the intended use. Graphics, DLL support and speed vary." : "JITless needs a 32-bit x86 Windows game or RPG Maker web assets."))) }
            .onAppear { refreshFiles() }
            .alert("Remove exported IPA?", isPresented: $confirmRemoval, presenting: removal) { file in
                Button("Remove", role: .destructive) {
                    do {
                        try FileManager.default.removeItem(at: file)
                        message = "Export removed."
                    } catch { message = error.localizedDescription }
                    refreshFiles()
                }
                Button("Cancel", role: .cancel) {}
            } message: { _ in Text("Only this saved IPA will be deleted. Your installed game stays in the library.") }

        }
    }
    @MainActor private func select(_ root: URL) {
        let access = root.startAccessingSecurityScopedResource()
        defer { if access { root.stopAccessingSecurityScopedResource() } }
        folder = root
        let executable = try? LibraryModel.executable(entry.relativePath)
        supportsWin32 = executable.map(PortGamePackage.isWin32Game) ?? false
        supportsWeb = executable.flatMap { PortGamePackage.webIndex(for: $0, inside: root) } != nil
        confirm = true
    }

    @MainActor private func build(_ root: URL, jitless: Bool) async {
        guard !busy else { return }
        busy = true; message = ""
        defer { busy = false }
        let access = root.startAccessingSecurityScopedResource()
        defer { if access { root.stopAccessingSecurityScopedResource() } }
        do {
            let exe = try LibraryModel.executable(entry.relativePath)
            let e = entry
            _ = try await Task.detached(priority: .userInitiated) { try PortGamePackage.export(e, root: root, executable: exe, jitless: jitless) }.value
            refreshFiles()
            message = "Saved to Files → On My iPhone → Anker Port → Anker IPA."
        } catch { message = error.localizedDescription }
    }
    private func refreshFiles() {
        let fm = FileManager.default
        files = [false, true].flatMap { jitless -> [URL] in
            let current = PortGamePackage.savedIPA(entry.id, jitless: jitless)
            let old = PortGamePackage.savedIPA(entry.id, jitless: jitless, legacy: true)
            if fm.fileExists(atPath: old.path), !fm.fileExists(atPath: current.path) {
                do {
                    try fm.createDirectory(at: current.deletingLastPathComponent(), withIntermediateDirectories: true)
                    try fm.moveItem(at: old, to: current)
                } catch { message = error.localizedDescription }
            }
            return [current, old].filter { fm.fileExists(atPath: $0.path) }
        }
    }
}
