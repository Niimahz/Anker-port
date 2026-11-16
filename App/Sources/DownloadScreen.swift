import SwiftUI

struct DownloadScreen: View {
    @StateObject private var downloads = ConcurrentDownloads()
    @State private var link = ""
    @State private var fastMode = true
    @State private var concurrency = 3
    private var validURL: Bool {
        guard let url = URL(string: link.trimmingCharacters(in: .whitespacesAndNewlines)),
              let scheme = url.scheme?.lowercased(), ["http", "https"].contains(scheme),
              url.host != nil else { return false }
        return true
    }
    var body: some View {
        List {
            Section("New download") {
                TextField("https://example.com/game.zip", text: $link)
                    .textInputAutocapitalization(.never).keyboardType(.URL)
                    .autocorrectionDisabled()
                Toggle("Accelerated download", isOn: $fastMode)
                Stepper("Parallel downloads: \(concurrency)", value: $concurrency, in: 1...4)
                    .onChange(of: concurrency) { downloads.setLimit($0) }
                Button("Start download") {
                    downloads.add(link, mode: fastMode ? "fast" : "normal")
                    link = ""
                }.disabled(!validURL)
            }
            Section("Downloads") {
                ForEach(downloads.jobs) { job in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(job.url.lastPathComponent).font(.headline)
                        Text(job.state).font(.caption).foregroundStyle(.secondary)
                        if job.expected > 0 {
                            ProgressView(value: min(1, Double(job.received) / Double(job.expected)))
                            Text("\(ByteCountFormatter.string(fromByteCount: job.received, countStyle: .file)) / \(ByteCountFormatter.string(fromByteCount: job.expected, countStyle: .file))")
                                .font(.caption2).foregroundStyle(.secondary)
                        } else if job.received > 0 {
                            Text(ByteCountFormatter.string(fromByteCount: job.received, countStyle: .file))
                                .font(.caption2)
                        }
                        HStack {
                            if job.state == "Downloading" || job.state == "Connecting" {
                                Button("Pause") { downloads.pause(job) }
                            }
                            if job.state == "Paused" || job.state.hasPrefix("Failed:") {
                                Button("Resume") { downloads.resume(job) }
                            }
                            if job.state != "Completed" && job.state != "Cancelled" {
                                Button("Cancel", role: .destructive) { downloads.cancel(job) }
                            }
                            if job.state == "Completed" || job.state == "Cancelled" {
                                Button("Remove", role: .destructive) { _ = downloads.delete(job) }
                            }
                        }.buttonStyle(.borderless)
                        if let file = job.savedFile {
                            ShareLink("Share archive", item: file)
                        }
                    }.padding(.vertical, 4)
                }
            }
        }.navigationTitle("Downloads")
    }
}
