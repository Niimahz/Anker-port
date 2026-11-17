#!/usr/bin/env python3
"""Inject Anker download entry into the real Madeira app, retaining its Wine launch path."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: integrate-upstream.py UPSTREAM_ROOT")
source = Path(sys.argv[1]) / "app/Madeira/MadeiraApp.swift"
original = source.read_text()
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

private struct AnkerNativeDownloads: View {
    @StateObject private var model = AnkerDownloadModel()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                VStack(alignment: .leading, spacing: 8) {
                    Label("ANKER PORT", systemImage: "square.stack.3d.up.fill")
                        .font(.caption.weight(.heavy))
                        .tracking(2)
                        .foregroundStyle(.indigo)
                    Text("Your games. One place.")
                        .font(.largeTitle.bold())
                        .minimumScaleFactor(0.75)
                    Text("Manage downloads here. Launch installed Windows games from the Madeira library.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(22)
                .background(
                    LinearGradient(colors: [.indigo.opacity(0.13), .purple.opacity(0.06)],
                                   startPoint: .topLeading, endPoint: .bottomTrailing),
                    in: RoundedRectangle(cornerRadius: 22)
                )

                VStack(alignment: .leading, spacing: 14) {
                    Label("New download", systemImage: "arrow.down.circle.fill")
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
                    HStack {
                        Label("Downloaded files", systemImage: "folder.fill")
                            .font(.headline)
                        Spacer()
                        Text("\(model.files.count)")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                        Button { model.refresh() } label: {
                            Image(systemName: "arrow.clockwise")
                        }
                        .accessibilityLabel("Refresh downloads")
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

                Label("Archives are saved to Documents/AnkerDownloads. Automatic extraction and game-library import are not enabled yet.",
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
    }
}
'''
source.write_text(original)
print("Added Anker Downloads to the real Madeira application entry point.")
