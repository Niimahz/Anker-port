import SwiftUI

struct TuningScreen: View {
    let folder: URL
    @State private var tuning = GameTuning()
    @State private var status = ""
    var body: some View {
        Form {
            Section("Display") {
                Picker("Resolution", selection: Binding(
                    get: { "\(tuning.resolutionWidth)x\(tuning.resolutionHeight)" },
                    set: {
                        let parts = $0.split(separator: "x").compactMap(Int.init)
                        if parts.count == 2 { tuning.resolutionWidth = parts[0]; tuning.resolutionHeight = parts[1] }
                    }
                )) {
                    Text("640 × 480").tag("640x480")
                    Text("960 × 540").tag("960x540")
                    Text("1280 × 720").tag("1280x720")
                    Text("1920 × 1080").tag("1920x1080")
                }
                Picker("FPS target", selection: $tuning.fpsLimit) {
                    Text("30").tag(30)
                    Text("40").tag(40)
                    Text("60").tag(60)
                    Text("Unlimited").tag(0)
                }
                Toggle("Virtual desktop", isOn: $tuning.virtualDesktop)
            }
            Section("Graphics compatibility") {
                Picker("Graphics backend", selection: $tuning.graphicsBackend) {
                    ForEach(GameTuning.GraphicsBackend.allCases) { backend in
                        Text(backend.rawValue).tag(backend)
                    }
                }
                Toggle("Detailed diagnostic logging", isOn: $tuning.debugLogging)
            }
            Section("Advanced") {
                TextField("Launch arguments", text: $tuning.launchArguments, axis: .vertical)
                TextField("Environment (one KEY=VALUE per line)", text: $tuning.environmentText, axis: .vertical)
                    .lineLimit(3...8)
            }
            Section {
                Button("Save game settings") {
                    do {
                        try GameTuningStore.save(tuning, for: folder)
                        status = "Saved locally"
                    } catch { status = error.localizedDescription }
                }
                if !status.isEmpty { Text(status).font(.caption) }
                Text("These settings are stored now. Applying them to a running Windows game requires the native runtime to be linked.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Game settings")
        .onAppear { tuning = GameTuningStore.load(for: folder) }
    }
}
