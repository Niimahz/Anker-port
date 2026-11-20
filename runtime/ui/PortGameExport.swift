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

    static func export(_ entry: LibraryEntry, root: URL, executable: URL, jitless: Bool) throws -> URL {
        let fm = FileManager.default
        let source = root.resolvingSymlinksInPath().standardizedFileURL
        let exe = executable.resolvingSymlinksInPath().standardizedFileURL
        let drive = LibraryModel.drive.standardizedFileURL
        guard source != drive, source.path != drive.path,
              !drive.path.hasPrefix(source.path + "/"), exe.path.hasPrefix(source.path + "/"),
              exe.pathExtension.lowercased() == "exe", fm.fileExists(atPath: exe.path) else {
            throw PortGamePackageError("Select the individual game folder containing this EXE and its assets.")
        }
        let index = jitless ? webIndex(for: exe, inside: source) : nil
        if jitless && index == nil {
            throw PortGamePackageError("JITless export needs RPG Maker MV or MZ browser assets beside the game EXE.")
        }
        let seedInfo = try Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("PortSeed.plist"))
        guard let metadata = try PropertyListSerialization.propertyList(from: seedInfo, format: nil) as? [String: Any],
              var info = metadata["info"] as? [String: Any], let prefix = metadata["prefix"] as? String else {
            throw PortGamePackageError("The export template is incomplete.")
        }
        let temp = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try fm.createDirectory(at: temp, withIntermediateDirectories: true)
        let exported = temp.appendingPathComponent("Game-" + entry.id.uuidString + (jitless ? "-JITless.ipa" : "-WithJIT.ipa"))
        do {
            info["CFBundleIdentifier"] = "app.ankerport.game.g" + entry.id.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
            if let index {
                info["AnkerWebIndex"] = String(index.path.dropFirst(source.path.count + 1))
                info["CFBundleIdentifier"] = "app.ankerport.game.web.g" + entry.id.uuidString.lowercased().replacingOccurrences(of: "-", with: "")
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
                let actual = drive.appendingPathComponent(path).standardizedFileURL.path
                if actual == source.path || actual.hasPrefix(source.path + "/") {
                    game.workingDirectory = "C:\\Games\\AnkerStandalone\\" + entry.id.uuidString + String(actual.dropFirst(source.path.count)).replacingOccurrences(of: "/", with: "\\")
                }
            }
            let manifest = temp.appendingPathComponent("PortGame.json")
            try JSONEncoder().encode(game).write(to: manifest)
            var error = [CChar](repeating: 0, count: 512)
            guard port_build_ipa(seed.path, prefix, source.path, plist.path, manifest.path, exported.path, &error, 512) == 0 else {
                throw PortGamePackageError(String(cString: error))
            }
            try fm.removeItem(at: plist)
            try fm.removeItem(at: manifest)
            return exported
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
    init(directory: URL) { self.directory = directory.resolvingSymlinksInPath().standardizedFileURL }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, url.host == "game" else {
            task.didFailWithError(URLError(.badURL))
            return
        }
        let file = directory.appendingPathComponent(url.path).resolvingSymlinksInPath().standardizedFileURL
        guard file.path.hasPrefix(directory.path + "/") else {
            task.didFailWithError(URLError(.noPermissionsToReadFile))
            return
        }
        do {
            let bytes = try Data(contentsOf: file, options: .mappedIfSafe)
            let mime = UTType(filenameExtension: file.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
            task.didReceive(URLResponse(url: url, mimeType: mime, expectedContentLength: bytes.count, textEncodingName: nil))
            task.didReceive(bytes)
            task.didFinish()
        } catch { task.didFailWithError(error) }
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}

private struct PortWebGame: UIViewRepresentable {
    let directory: URL

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.setURLSchemeHandler(PortWebAssets(directory: directory), forURLScheme: "ankergame")
        let view = WKWebView(frame: .zero, configuration: configuration)
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
        if let index = Bundle.main.object(forInfoDictionaryKey: "AnkerWebIndex") as? String {
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
            if let ready { Button("Play") { model.error = nil; play(ready) }.buttonStyle(.borderedProminent) }
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

private struct PortSaveIPA: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        UIDocumentPickerViewController(forExporting: [url], asCopy: true)
    }
    func updateUIViewController(_ controller: UIDocumentPickerViewController, context: Context) {}
}

struct PortExportSection: View {
    let entry: LibraryEntry
    @State private var choose = false
    @State private var confirm = false
    @State private var supportsWeb = false
    @State private var folder: URL?
    @State private var busy = false
    @State private var message = ""
    @State private var result: URL?
    @State private var saving = false

    var body: some View {
        if !PortGamePackage.standalone && entry.relativePath.lowercased().hasSuffix(".exe") && entry.desktop != true {
            Section {
                Button {
                    if let root = PortGamePackage.importedRoot(entry) { select(root) }
                    else { choose = true }
                } label: { Label("Export game IPA", systemImage: "shippingbox") }.disabled(busy)
                if busy { ProgressView("Packaging runtime and game files…") }
                if !message.isEmpty { Text(message).font(.footnote) }
            } footer: { Text("Includes every file in the selected game folder and a separate runtime. Choose With JIT for Windows execution or JITless for games with RPG Maker MV/MZ browser assets. Windows-only plugins require With JIT. Store clients and system-wide dependencies may need separate setup.") }
            .fileImporter(isPresented: $choose, allowedContentTypes: [.folder]) { value in
                do { select(try value.get()) } catch { message = error.localizedDescription }
            }
            .confirmationDialog("Export game IPA", isPresented: $confirm, titleVisibility: .visible) {
                Button("With JIT") { if let folder { Task { await build(folder, jitless: false) } } }
                Button("JITless · RPG Maker Web") { if let folder { Task { await build(folder, jitless: true) } } }.disabled(!supportsWeb)
                Button("Cancel", role: .cancel) {}
            } message: { Text("Includes the entire game folder. " + (supportsWeb ? "Browser assets detected. Windows-only plugins may be incompatible." : "JITless unavailable for this game: no RPG Maker MV/MZ browser assets found.")) }
            .sheet(isPresented: $saving, onDismiss: clean) {
                if let result { PortSaveIPA(url: result) }
            }
        }
    }
    @MainActor private func select(_ root: URL) {
        let access = root.startAccessingSecurityScopedResource()
        defer { if access { root.stopAccessingSecurityScopedResource() } }
        folder = root
        supportsWeb = (try? LibraryModel.executable(entry.relativePath)).flatMap { PortGamePackage.webIndex(for: $0, inside: root) } != nil
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
            result = try await Task.detached(priority: .userInitiated) { try PortGamePackage.export(e, root: root, executable: exe, jitless: jitless) }.value
            saving = true
        } catch { message = error.localizedDescription }
    }
    private func clean() {
        if let result { try? FileManager.default.removeItem(at: result.deletingLastPathComponent()) }
        result = nil
    }
}
