import WebKit

struct AnkerHome: View {
    @ObservedObject var library: LibraryModel
    let play: (LibraryEntry) -> Void
    let select: (Int) -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                let latest = library.entries.max { ($0.lastPlayed ?? .distantPast) < ($1.lastPlayed ?? .distantPast) }
                VStack(alignment: .leading, spacing: 20) {
                    HStack(alignment: .top) {
                        Label("ANKER PORT", systemImage: "gamecontroller.fill")
                            .font(.caption.bold()).tracking(2)
                        Spacer()
                        if let latest {
                            LibraryArtwork(entry: latest)
                                .frame(width: 62, height: 80)
                                .clipShape(RoundedRectangle(cornerRadius: 9))
                                .accessibilityHidden(true)
                        }
                    }
                    Spacer(minLength: 20)
                    Text(latest?.title ?? "Game library")
                        .font(.system(.largeTitle, design: .rounded, weight: .bold))
                    Button {
                        if let latest { play(latest) } else { select(2) }
                    } label: {
                        Label(latest == nil ? "Import a game" : "Play game", systemImage: latest == nil ? "plus" : "play.fill")
                    }.buttonStyle(.borderedProminent).tint(.white).foregroundStyle(.black)
                }
                .foregroundStyle(.white).padding(24)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(LinearGradient(colors: [Color(red: 0.06, green: 0.15, blue: 0.21), Color(red: 0.02, green: 0.38, blue: 0.40)], startPoint: .topLeading, endPoint: .bottomTrailing), in: RoundedRectangle(cornerRadius: 26))
                Button { select(0) } label: {
                    HStack {
                        Label("Game library", systemImage: "square.grid.2x2.fill")
                        Spacer()
                        Text(String(library.entries.count)).monospacedDigit()
                        Image(systemName: "chevron.right").font(.caption)
                    }.padding(18)
                }.buttonStyle(.plain).background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
                if !library.entries.isEmpty {
                    Text("Games").font(.title2.bold())
                    ScrollView(.horizontal) {
                        LazyHStack(alignment: .top, spacing: 14) {
                            ForEach(library.entries.prefix(12)) { entry in
                                Button {
                                    select(0)
                                    library.showDetail = entry.id
                                } label: {
                                    VStack(alignment: .leading, spacing: 9) {
                                        LibraryArtwork(entry: entry)
                                            .frame(width: 108, height: 150)
                                            .clipShape(RoundedRectangle(cornerRadius: 12))
                                        Text(entry.title).font(.subheadline.bold()).lineLimit(2)
                                    }.frame(width: 108, alignment: .leading)
                                }.buttonStyle(.plain)
                            }
                        }
                    }.scrollIndicators(.hidden)
                }
                HStack {
                    shortcut("Downloads", "arrow.down.circle", 2)
                    shortcut("Browser", "safari", 3)
                }
            }.padding(18).frame(maxWidth: 720)
            .frame(maxWidth: .infinity)
        }.background(Color(uiColor: .systemGroupedBackground))
    }

    private func shortcut(_ title: String, _ icon: String, _ tab: Int) -> some View {
        Button { select(tab) } label: {
            VStack(alignment: .leading, spacing: 16) {
                Image(systemName: icon).font(.title2).foregroundStyle(.teal)
                Text(title).font(.headline)
            }.padding(18).frame(maxWidth: .infinity, alignment: .leading)
        }.buttonStyle(.plain).background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}

@MainActor
final class AnkerWebSession: NSObject, ObservableObject, WKNavigationDelegate, WKDownloadDelegate {
    let page = WKWebView()
    @Published var address = ""
    @Published var status = ""
    @Published var back = false
    @Published var forward = false

    override init() {
        super.init()
        page.navigationDelegate = self
        page.allowsBackForwardNavigationGestures = true
    }

    func openAddress() {
        let input = address.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !input.isEmpty else { return }
        let hasScheme = URLComponents(string: input)?.scheme != nil
        let candidate = hasScheme ? input : "https://" + input
        if !input.contains(" "), (hasScheme || input.contains(".")), let url = URL(string: candidate),
           ["https", "http"].contains(url.scheme?.lowercased() ?? ""), url.host != nil {
            page.load(URLRequest(url: url))
        } else if !hasScheme {
            var search = URLComponents(string: "https://duckduckgo.com/")!
            search.queryItems = [URLQueryItem(name: "q", value: input)]
            if let url = search.url { page.load(URLRequest(url: url)) }
        } else { status = "Enter a web address using HTTP or HTTPS." }
    }
    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) { status = "Loading…" }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        address = webView.url?.absoluteString ?? address
        back = webView.canGoBack
        forward = webView.canGoForward
        status = ""
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { report(error) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { report(error) }
    private func report(_ error: Error) {
        if (error as NSError).code != NSURLErrorCancelled { status = error.localizedDescription }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if action.shouldPerformDownload { decisionHandler(.download); return }
        if action.targetFrame == nil {
            decisionHandler(.cancel)
            webView.load(action.request)
        } else { decisionHandler(.allow) }
    }
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        let disposition = (response.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        decisionHandler(response.canShowMIMEType && !disposition.lowercased().hasPrefix("attachment") ? .allow : .download)
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        do {
            let dir = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask, appropriateFor: nil, create: true).appendingPathComponent("AnkerDownloads")
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            let name = (suggestedFilename as NSString).lastPathComponent
            status = "Downloading " + name
            completionHandler(dir.appendingPathComponent(UUID().uuidString + "-" + (name.isEmpty || name == "/" ? "download" : name)))
        } catch { status = error.localizedDescription; completionHandler(nil) }
    }
    func downloadDidFinish(_ download: WKDownload) { status = "Saved to Downloads" }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) { status = error.localizedDescription }
}

private struct AnkerWebPage: UIViewRepresentable {
    let page: WKWebView
    func makeUIView(context: Context) -> WKWebView { page }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}

struct AnkerBrowser: View {
    @ObservedObject var session: AnkerWebSession
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "globe").foregroundStyle(.teal)
                TextField("Search or enter website", text: $session.address)
                    .keyboardType(.webSearch).textInputAutocapitalization(.never)
                    .autocorrectionDisabled().submitLabel(.go).onSubmit { session.openAddress() }
                Button { session.openAddress() } label: { Image(systemName: "arrow.right.circle.fill") }.accessibilityLabel("Go")
            }.padding(12).background(.thinMaterial, in: Capsule()).padding(.horizontal)
            if !session.status.isEmpty { Text(session.status).font(.caption).padding(6) }
            AnkerWebPage(page: session.page)
            HStack {
                Button { session.page.goBack() } label: { Label("Back", systemImage: "chevron.left") }.disabled(!session.back)
                Spacer()
                Button { session.page.reload() } label: { Label("Reload", systemImage: "arrow.clockwise") }
                Spacer()
                Button { session.page.goForward() } label: { Label("Forward", systemImage: "chevron.right") }.disabled(!session.forward)
            }.font(.subheadline).padding()
        }
    }
}
