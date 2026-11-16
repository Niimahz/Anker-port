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
// This lives inside the upstream runtime target; it does not replace Wine/FEX/DXMT.
private struct AnkerDownloadEntry: View {
    @State private var showingDownloads = false
    var body: some View {
        Button {
            showingDownloads = true
        } label: {
            Label("Anker Downloads", systemImage: "arrow.down.circle.fill")
                .font(.caption.weight(.semibold))
                .padding(8)
                .background(.regularMaterial, in: Capsule())
        }
        .accessibilityIdentifier("anker.downloads.open")
        .sheet(isPresented: $showingDownloads) {
            NavigationStack { AnkerNativeDownloads() }
        }
    }
}

private struct AnkerNativeDownloads: View {
    @State private var address = ""
    @State private var status = "Downloads are saved to Documents/AnkerDownloads."
    @State private var busy = false
    @State private var saved: URL?
    @Environment(\.dismiss) private var dismiss

    private var validatedURL: URL? {
        guard let url = URL(string: address.trimmingCharacters(in: .whitespacesAndNewlines)),
              let scheme = url.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              url.host != nil else { return nil }
        return url
    }

    var body: some View {
        Form {
            Section("Download game archive") {
                TextField("https://example.com/game.zip", text: $address)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                Button(busy ? "Downloading…" : "Download") {
                    guard let url = validatedURL else { return }
                    busy = true
                    status = "Downloading " + url.lastPathComponent
                    Task { await download(url) }
                }
                .disabled(busy || validatedURL == nil)
                if busy { ProgressView() }
            }
            Section("Status") {
                Text(status)
                if let saved {
                    ShareLink("Share downloaded file", item: saved)
                }
                Text("Archives are not automatically extracted or added to the Wine library yet.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Anker Downloads")
        .toolbar { ToolbarItem(placement: .confirmationAction) {
            Button("Done") { dismiss() }
        }}
    }

    @MainActor
    private func download(_ url: URL) async {
        defer { busy = false }
        do {
            let (temporary, response) = try await URLSession.shared.download(from: url)
            guard let http = response as? HTTPURLResponse,
                  (200...299).contains(http.statusCode) else {
                status = "Server did not return a successful HTTP response."
                return
            }
            let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("AnkerDownloads", isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let candidate = response.suggestedFilename ?? url.lastPathComponent
            let name = URL(fileURLWithPath: candidate).lastPathComponent
            let safeName = name.isEmpty || name == "/" ? "download.bin" : name
            let destination = directory.appendingPathComponent(UUID().uuidString + "-" + safeName)
            try FileManager.default.moveItem(at: temporary, to: destination)
            saved = destination
            status = "Saved: " + destination.lastPathComponent
        } catch {
            status = "Download failed: " + error.localizedDescription
        }
    }
}
'''
source.write_text(original)
print("Added Anker Downloads to the real Madeira application entry point.")
