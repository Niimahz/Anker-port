import SwiftUI
import UniformTypeIdentifiers

struct LibraryScreen: View {
    @State private var archives: [URL] = []
    @State private var games: [URL] = []
    @State private var showImporter = false
    @State private var status = ""
    @State private var busy = false

    var body: some View {
        List {
            Section("Import") {
                Button("Import archive from Files") { showImporter = true }
                Text(status).font(.caption).foregroundStyle(.secondary)
            }
            Section("Downloaded archives") {
                ForEach(archives, id: \.path) { file in
                    HStack {
                        Text(file.lastPathComponent).lineLimit(2)
                        Spacer()
                        Button("Extract") { extract(file) }.disabled(busy)
                    }
                }
            }
            Section("My Games") {
                ForEach(games, id: \.path) { folder in
                    NavigationLink(folder.lastPathComponent) {
                        GameDetailScreen(folder: folder)
                    }
                }
            }
        }
        .navigationTitle("Game Library")
        .toolbar { Button("Refresh", systemImage: "arrow.clockwise") { refresh() } }
        .onAppear { refresh() }
        .fileImporter(isPresented: $showImporter, allowedContentTypes: [.item]) { result in
            switch result {
            case .success(let url):
                busy = true
                Task.detached {
                    let result = Result { try GameLibrary.importArchive(url) }
                    await MainActor.run {
                        busy = false
                        switch result {
                        case .success(let saved): status = "Imported " + saved.lastPathComponent
                        case .failure(let error): status = error.localizedDescription
                        }
                        refresh()
                    }
                }
            case .failure(let error): status = error.localizedDescription
            }
        }
    }

    private func refresh() {
        try? GameLibrary.ensureFolders()
        archives = GameLibrary.files(in: GameLibrary.downloads)
        games = GameLibrary.files(in: GameLibrary.games).filter {
            (try? $0.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true
        }
    }
    private func extract(_ url: URL) {
        busy = true
        status = "Extracting..."
        Task.detached {
            let result = Result { try GameLibrary.extract(url) }
            await MainActor.run {
                busy = false
                switch result {
                case .success(let folder): status = "Ready: " + folder.lastPathComponent
                case .failure(let error): status = "Extraction failed: " + error.localizedDescription
                }
                refresh()
            }
        }
    }
}

struct GameDetailScreen: View {
    let folder: URL
    @State private var report: GameReport?
    @State private var status = ""
    @State private var selectedExecutable: String?
    var body: some View {
        List {
            Section("Game") {
                Text(folder.lastPathComponent)
                Button("Analyze game files") {
                    do { report = try GameAnalyzer.analyze(folder: folder) }
                    catch { status = error.localizedDescription }
                }
            }
            if let report {
                Section("Executables") {
                    ForEach(report.executables.filter { $0.path.lowercased().hasSuffix(".exe") }) { file in
                        Button {
                            selectedExecutable = file.path
                        } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(file.path)
                                    Text(file.architecture).font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                                if selectedExecutable == file.path { Image(systemName: "checkmark.circle.fill") }
                            }
                        }
                    }
                }
            }
            Section("Launcher") {
                NavigationLink("Compatibility & performance settings") { TuningScreen(folder: folder) }
                Text(RuntimeLauncher.isAvailable ? "Runtime ready" : "Native runtime is not linked in this build.")
                    .font(.caption)
                Button("Launch game") {
                    guard let selectedExecutable else { return }
                    do {
                        let tuning = GameTuningStore.load(for: folder)
                        let request = RuntimeLaunchRequest(gameFolder: folder, executable: folder.appendingPathComponent(selectedExecutable), arguments: tuning.arguments, environment: tuning.environment)
                        let result = try RuntimeLauncher.launch(request)
                        status = result.diagnostic
                    } catch { status = error.localizedDescription }
                }.disabled(!RuntimeLauncher.isAvailable || selectedExecutable == nil)
            }
            if !status.isEmpty { Text(status) }
        }.navigationTitle("Game")
    }
}
