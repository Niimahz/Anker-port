import SwiftUI

struct DownloadScreen: View {
    @StateObject private var downloads = ConcurrentDownloads()
    @State private var link = ""
    @State private var fastMode = true
    var body: some View {
        List {
            Section("New download") {
                TextField("https://example.com/game.zip", text: $link)
                    .textInputAutocapitalization(.never).keyboardType(.URL)
                    .autocorrectionDisabled()
                Toggle("Accelerated download (when supported)", isOn: $fastMode)
                Button("Start download") {
                    downloads.add(link, mode: fastMode ? "fast" : "normal")
                    link = ""
                }.disabled(URL(string: link)?.scheme?.lowercased().map { !["http", "https"].contains($0) } ?? true)
            }
            Section("Downloads") {
                ForEach(downloads.jobs) { job in
                    VStack(alignment: .leading, spacing: 5) {
                        Text(job.url.lastPathComponent).font(.headline)
                        Text(job.state).font(.caption)
                        if job.expected > 0 {
                            ProgressView(value: Double(job.received), total: Double(job.expected))
                        }
                        if let file = job.savedFile { Text(file.lastPathComponent).font(.caption).textSelection(.enabled) }
                    }
                }
            }
        }.navigationTitle("Downloads")
    }
}
