import WebKit

enum PortStyle {
    static let ground = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark ? UIColor(red: 0.06, green: 0.068, blue: 0.078, alpha: 1) : UIColor(red: 0.955, green: 0.948, blue: 0.927, alpha: 1)
    })
    static let panel = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark ? UIColor(red: 0.105, green: 0.115, blue: 0.13, alpha: 1) : .white
    })
    static let signal = Color(red: 1, green: 0.53, blue: 0.30)
    static let accent = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark ? UIColor(red: 1, green: 0.53, blue: 0.30, alpha: 1) : UIColor(red: 0.66, green: 0.22, blue: 0.055, alpha: 1)
    })
}

extension View {
    func portPanel() -> some View {
        background(PortStyle.panel, in: RoundedRectangle(cornerRadius: 19))
            .overlay { RoundedRectangle(cornerRadius: 19).strokeBorder(.primary.opacity(0.09)) }
    }
}

struct PortMark: View {
    var body: some View {
        Canvas { context, size in
            let w = size.width, h = size.height
            var path = Path()
            for (x, y) in [(0.04,0.80),(0.40,0.12),(0.64,0.12),(0.28,0.80)] {
                let point = CGPoint(x: w * CGFloat(x), y: h * CGFloat(y))
                if path.isEmpty { path.move(to: point) } else { path.addLine(to: point) }
            }
            path.closeSubpath()
            path.move(to: CGPoint(x: w*0.56, y: h*0.54))
            path.addLine(to: CGPoint(x: w*0.69, y: h*0.30))
            path.addLine(to: CGPoint(x: w*0.96, y: h*0.80))
            path.addLine(to: CGPoint(x: w*0.70, y: h*0.80))
            path.closeSubpath()
            context.fill(path, with: .color(PortStyle.signal))
        }.accessibilityHidden(true)
    }
}

struct PortDock: View {
    let tab: Int
    let select: (Int) -> Void
    private let items = [(4,"Home","house.fill"), (0,"Library","square.grid.2x2.fill"), (2,"Downloads","arrow.down.to.line"), (3,"Browser","safari"), (1,"Settings","slider.horizontal.3")]
    var body: some View {
        HStack(spacing: 1) {
            ForEach(items, id: \.0) { item in
                Button { select(item.0) } label: {
                    VStack(spacing: 4) {
                        Image(systemName: item.2).font(.system(size: 17, weight: .semibold))
                        Text(item.1).font(.caption2.weight(.semibold)).lineLimit(1).minimumScaleFactor(0.68)
                    }
                    .frame(maxWidth: .infinity, minHeight: 48)
                    .foregroundStyle(tab == item.0 ? Color.black : Color.white.opacity(0.8))
                    .background(tab == item.0 ? PortStyle.signal : Color.clear, in: RoundedRectangle(cornerRadius: 13))
                }.buttonStyle(.plain).accessibilityAddTraits(tab == item.0 ? .isSelected : [])
            }
        }.padding(5).frame(maxWidth: 540)
        .background(Color(white: 0.105), in: RoundedRectangle(cornerRadius: 18))
        .padding(.horizontal, 12).padding(.vertical, 4)
        .frame(maxWidth: .infinity).background(PortStyle.ground)
    }
}

struct AnkerHome: View {
    @ObservedObject var library: LibraryModel
    let play: (LibraryEntry) -> Void
    let select: (Int) -> Void
    private var games: [LibraryEntry] { library.entries.filter { $0.desktop != true && $0.listedInLibrary } }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                let latest = games.max { ($0.lastPlayed ?? .distantPast) < ($1.lastPlayed ?? .distantPast) }
                VStack(alignment: .leading, spacing: 16) {
                    Spacer(minLength: 76)
                    Text(latest?.title ?? "Your game library")
                        .font(.system(.largeTitle, design: .rounded, weight: .heavy))
                        .lineLimit(3).foregroundStyle(.white)
                    Button {
                        if let latest { play(latest) } else { select(0) }
                    } label: {
                        Label(latest == nil ? "Open library" : "Play game", systemImage: latest == nil ? "square.grid.2x2.fill" : "play.fill")
                            .font(.headline).padding(.horizontal, 18).frame(minHeight: 44)
                            .foregroundStyle(.black).background(PortStyle.signal, in: Capsule())
                    }.buttonStyle(.plain)
                }.padding(22).frame(maxWidth: .infinity, alignment: .leading)
                .background {
                    GeometryReader { g in
                        ZStack(alignment: .trailing) {
                            Color(white: 0.09)
                            if let latest {
                                LibraryArtwork(entry: latest).frame(width: g.size.width * 0.63, height: g.size.height).clipped()
                            } else {
                                PortMark().frame(width: g.size.width * 0.6, height: g.size.height).opacity(0.7)
                            }
                            LinearGradient(colors: [Color(white: 0.09), .black.opacity(0.08)], startPoint: .leading, endPoint: .trailing)
                            LinearGradient(colors: [.clear, .black.opacity(0.72)], startPoint: .top, endPoint: .bottom)
                        }.frame(width: g.size.width, height: g.size.height)
                    }
                }.clipShape(RoundedRectangle(cornerRadius: 24))
                HStack(spacing: 10) {
                    shortcut("Downloads", "arrow.down.to.line", 2)
                    shortcut("Browser", "safari", 3)
                }
                Button { select(0) } label: {
                    HStack { Text("Library").font(.title2.bold()); Spacer(); Text(String(games.count)).monospacedDigit(); Image(systemName: "arrow.up.right") }
                }.buttonStyle(.plain)
                if !games.isEmpty {
                    ScrollView(.horizontal) {
                        LazyHStack(alignment: .top, spacing: 12) {
                            ForEach(games.prefix(12)) { entry in
                                Button { select(0); library.showDetail = entry.id } label: {
                                    VStack(alignment: .leading, spacing: 8) {
                                        LibraryArtwork(entry: entry).frame(width: 118, height: 157).clipShape(RoundedRectangle(cornerRadius: 12))
                                        Text(entry.title).font(.subheadline.bold()).lineLimit(2)
                                    }.frame(width: 118, alignment: .leading)
                                }.buttonStyle(.plain)
                            }
                        }
                    }.scrollIndicators(.hidden)
                }
            }.padding(18).frame(maxWidth: 760).frame(maxWidth: .infinity)
        }.background(PortStyle.ground)
    }
    private func shortcut(_ title: String, _ icon: String, _ tab: Int) -> some View {
        Button { select(tab) } label: {
            VStack(alignment: .leading, spacing: 18) {
                Image(systemName: icon).font(.title2).foregroundStyle(PortStyle.accent)
                Text(title).font(.headline)
            }.padding(16).frame(maxWidth: .infinity, alignment: .leading).portPanel()
        }.buttonStyle(.plain)
    }
}

@MainActor
final class AnkerWebSession: NSObject, ObservableObject, WKNavigationDelegate, WKDownloadDelegate {
    private var destinations: [ObjectIdentifier: (temporary: URL, final: URL)] = [:]
    let page = WKWebView()
    @Published var address = ""
    @Published var status = ""
    @Published var hasPage = false
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
    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) { hasPage = true; status = "Loading…" }
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
            let final = dir.appendingPathComponent(UUID().uuidString + "-" + (name.isEmpty || name == "/" ? "download" : name))
            let temporary = dir.appendingPathComponent(".download-" + UUID().uuidString)
            destinations[ObjectIdentifier(download)] = (temporary, final)
            completionHandler(temporary)
        } catch { status = error.localizedDescription; completionHandler(nil) }
    }
    func downloadDidFinish(_ download: WKDownload) {
        guard let paths = destinations.removeValue(forKey: ObjectIdentifier(download)) else { return }
        do {
            try FileManager.default.moveItem(at: paths.temporary, to: paths.final)
            AnkerDownloadModel.shared.didSave(paths.final)
            status = "Saved to Downloads"
        } catch { status = error.localizedDescription }
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        if let paths = destinations.removeValue(forKey: ObjectIdentifier(download)) {
            try? FileManager.default.removeItem(at: paths.temporary)
        }
        status = error.localizedDescription
    }
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
                Image(systemName: "globe").foregroundStyle(PortStyle.accent)
                TextField("Search or enter website", text: $session.address)
                    .keyboardType(.webSearch).textInputAutocapitalization(.never)
                    .autocorrectionDisabled().submitLabel(.go).onSubmit { session.openAddress() }
                Button { session.openAddress() } label: { Image(systemName: "arrow.right.circle.fill") }.accessibilityLabel("Go")
            }.padding(12).portPanel().padding(.horizontal, 12).padding(.bottom, 8)
            if !session.status.isEmpty { Text(session.status).font(.caption).padding(6) }
            if session.hasPage {
                AnkerWebPage(page: session.page)
            } else {
                VStack(alignment: .leading, spacing: 18) {
                    Text("Browser").font(.system(.largeTitle, design: .rounded, weight: .heavy))
                    ForEach(["store.steampowered.com", "gog.com", "itch.io"], id: \.self) { host in
                        Button { session.address = host; session.openAddress() } label: {
                            HStack {
                                Image(systemName: "globe").foregroundStyle(PortStyle.accent)
                                Text(host).font(.headline)
                                Spacer()
                                Image(systemName: "arrow.up.right")
                            }.padding(16).portPanel()
                        }.buttonStyle(.plain)
                    }
                }.padding(18).frame(maxWidth: 700).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            }
            HStack {
                Button { session.page.goBack() } label: { Label("Back", systemImage: "chevron.left") }.disabled(!session.back)
                Spacer()
                Button { session.page.reload() } label: { Label("Reload", systemImage: "arrow.clockwise") }
                Spacer()
                Button { session.page.goForward() } label: { Label("Forward", systemImage: "chevron.right") }.disabled(!session.forward)
            }.font(.subheadline.weight(.semibold)).padding(12).background(PortStyle.panel)
        }.background(PortStyle.ground)
    }
}
