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

struct PortPress: ButtonStyle {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed && !reduceMotion ? 0.975 : 1)
            .opacity(configuration.isPressed ? 0.82 : 1)
            .animation(reduceMotion ? nil : .spring(duration: 0.24, bounce: 0.14), value: configuration.isPressed)
    }
}

// Machined copper contours, drawn once per size and composited as a single layer.
struct PortContours: View {
    var body: some View {
        Canvas { ctx, size in
            let unit = max(size.width, size.height)
            let center = CGPoint(x: size.width * 0.77, y: size.height * 0.45)
            for ring in 0..<38 {
                let depth = Double(ring) / 37
                var curve = Path()
                for step in 0...112 {
                    let t = Double(step) * 2 * Double.pi / 112
                    let wave = 1.0 + 0.16 * sin(3 * t + depth * 2)
                    let radius = (0.19 + 0.15 * depth) * wave
                    let x = radius * cos(t)
                    let y = radius * sin(t) * 0.70
                    let point = CGPoint(x: center.x + unit * CGFloat(x + y * 0.44),
                                        y: center.y + unit * CGFloat(y - x * 0.48 + depth * 0.15))
                    if step == 0 { curve.move(to: point) } else { curve.addLine(to: point) }
                }
                curve.closeSubpath()
                ctx.stroke(curve, with: .linearGradient(
                    Gradient(colors: [Color(red: 0.46, green: 0.13, blue: 0.07), PortStyle.signal,
                                      Color(red: 1, green: 0.87, blue: 0.69), Color(white: 0.20)]),
                    startPoint: .zero, endPoint: CGPoint(x: size.width, y: size.height * 0.35)),
                    lineWidth: 0.8 + CGFloat(depth) * 0.7)
            }
        }.accessibilityHidden(true).allowsHitTesting(false)
    }
}

struct PortPageHeading: View {
    let title: LocalizedStringKey
    let symbol: String
    var body: some View {
        HStack(alignment: .bottom) {
            Text(title).font(.system(.largeTitle, design: .rounded, weight: .heavy))
                .foregroundStyle(.white).accessibilityAddTraits(.isHeader)
            Spacer(minLength: 12)
            Image(systemName: symbol).font(.title2.bold()).foregroundStyle(PortStyle.signal)
                .accessibilityHidden(true)
        }.padding(20).frame(minHeight: 104, alignment: .bottom)
        .background {
            ZStack {
                Color(red: 0.13, green: 0.10, blue: 0.11)
                PortContours().opacity(0.36)
                LinearGradient(colors: [.black.opacity(0.68), .clear], startPoint: .leading, endPoint: .trailing)
            }
        }.clipShape(RoundedRectangle(cornerRadius: 20))
    }
}

struct PortActivity: View {
    let label: String
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        HStack(spacing: 9) {
            if reduceMotion { Image(systemName: "hourglass") }
            else { ProgressView().controlSize(.small).tint(PortStyle.accent) }
            Text(label).font(.footnote.weight(.semibold))
        }.foregroundStyle(PortStyle.accent).accessibilityElement(children: .combine)
    }
}

private struct PortSpotlight: View {
    let entry: LibraryEntry?
    let action: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Spacer(minLength: 92)
            Text(entry?.title ?? "Your game library")
                .font(.system(.largeTitle, design: .rounded, weight: .heavy)).lineLimit(3)
                .foregroundStyle(.white).accessibilityAddTraits(.isHeader)
            Button(action: action) {
                Label(entry == nil ? "Open library" : "Play game", systemImage: entry == nil ? "square.grid.2x2.fill" : "play.fill")
                    .font(.headline).padding(.horizontal, 20).frame(minHeight: 44)
                    .foregroundStyle(.black).background(PortStyle.signal, in: Capsule())
            }.buttonStyle(PortPress())
        }.padding(22).frame(maxWidth: .infinity, alignment: .leading)
        .background {
            GeometryReader { g in
                ZStack {
                    Color(red: 0.10, green: 0.09, blue: 0.10)
                    if let entry {
                        LibraryArtwork(entry: entry)
                            .frame(width: g.size.width, height: g.size.height).clipped()
                    } else { PortContours() }
                    LinearGradient(colors: [.clear, .black.opacity(0.87)], startPoint: .topTrailing, endPoint: .bottomLeading)
                }.frame(width: g.size.width, height: g.size.height).clipped()
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 25))
        .overlay { RoundedRectangle(cornerRadius: 25).strokeBorder(.white.opacity(0.16)) }
        .shadow(color: .black.opacity(0.18), radius: 10, y: 5)
        .scrollTransition(.interactive, axis: .vertical) { view, phase in
            view.scaleEffect(reduceMotion || phase.isIdentity ? 1 : 0.97)
        }
    }
}

struct PortDock: View {
    @Namespace private var selection
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let tab: Int
    let select: (Int) -> Void
    private let items = [(4,"Home","house.fill"), (0,"Library","square.grid.2x2.fill"), (2,"Downloads","arrow.down.to.line"), (3,"Browser","safari"), (1,"Settings","slider.horizontal.3")]
    var body: some View {
        HStack(spacing: 1) {
            ForEach(items, id: \.0) { item in
                Button { select(item.0) } label: {
                    HStack(spacing: 6) {
                        Image(systemName: item.2).font(.system(size: 17, weight: .semibold))
                        if tab == item.0 {
                            Text(item.1).font(.caption.bold()).lineLimit(1).minimumScaleFactor(0.72)
                        }
                    }
                    .padding(.horizontal, tab == item.0 ? 9 : 0)
                    .frame(minWidth: 44, maxWidth: tab == item.0 ? .infinity : 50, minHeight: 46)
                    .foregroundStyle(tab == item.0 ? Color.black : Color.white.opacity(0.85))
                    .background {
                        if tab == item.0 {
                            RoundedRectangle(cornerRadius: 13).fill(PortStyle.signal)
                                .matchedGeometryEffect(id: "tab", in: selection)
                        }
                    }
                }.buttonStyle(PortPress()).accessibilityLabel(item.1).accessibilityAddTraits(tab == item.0 ? .isSelected : [])
            }
        }.animation(reduceMotion ? nil : .spring(duration: 0.34, bounce: 0.17), value: tab)
        .sensoryFeedback(.selection, trigger: tab)
        .padding(5).frame(maxWidth: 540)
        .background(Color(white: 0.105), in: RoundedRectangle(cornerRadius: 18))
        .padding(.horizontal, 12).padding(.vertical, 4)
        .frame(maxWidth: .infinity).background(PortStyle.ground)
    }
}

struct AnkerHome: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @ObservedObject var library: LibraryModel
    let play: (LibraryEntry) -> Void
    let select: (Int) -> Void
    private var games: [LibraryEntry] { library.entries.filter { $0.desktop != true && $0.listedInLibrary } }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                let latest = games.max { ($0.lastPlayed ?? .distantPast) < ($1.lastPlayed ?? .distantPast) }
                PortSpotlight(entry: latest) {
                    if let latest { play(latest) } else { select(0) }
                }
                HStack(spacing: 10) {
                    shortcut("Downloads", "arrow.down.to.line", 2)
                    shortcut("Browser", "safari", 3)
                }
                Button { select(0) } label: {
                    HStack { Text("Library").font(.title2.bold()); Spacer(); Text(String(games.count)).monospacedDigit(); Image(systemName: "arrow.up.right") }
                }.buttonStyle(PortPress())
                if !games.isEmpty {
                    ScrollView(.horizontal) {
                        LazyHStack(alignment: .top, spacing: 12) {
                            ForEach(games.prefix(12)) { entry in
                                Button { select(0); library.showDetail = entry.id } label: {
                                    VStack(alignment: .leading, spacing: 8) {
                                        LibraryArtwork(entry: entry).frame(width: 118, height: 157).clipShape(RoundedRectangle(cornerRadius: 12))
                                        Text(entry.title).font(.subheadline.bold()).lineLimit(2)
                                    }.frame(width: 118, alignment: .leading)
                                    .scrollTransition(.interactive, axis: .horizontal) { view, phase in
                                        view.scaleEffect(reduceMotion || phase.isIdentity ? 1 : 0.94)
                                            .opacity(reduceMotion || phase.isIdentity ? 1 : 0.8)
                                    }
                                }.buttonStyle(PortPress())
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
        }.buttonStyle(PortPress())
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
                    PortPageHeading(title: "Browser", symbol: "safari")
                    ForEach(["store.steampowered.com", "gog.com", "itch.io"], id: \.self) { host in
                        Button { session.address = host; session.openAddress() } label: {
                            HStack {
                                Image(systemName: "globe").foregroundStyle(PortStyle.accent)
                                Text(host).font(.headline)
                                Spacer()
                                Image(systemName: "arrow.up.right")
                            }.padding(16).portPanel()
                        }.buttonStyle(PortPress())
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

struct PortCollectionWall: View {
    let games: [LibraryEntry]
    let searching: Bool
    let focused: UUID?
    let open: (LibraryEntry) -> Void
    let add: () -> Void

    var body: some View {
        if games.isEmpty {
            VStack(alignment: .leading, spacing: 14) {
                Image(systemName: searching ? "magnifyingglass" : "rectangle.stack.badge.plus")
                    .font(.largeTitle).foregroundStyle(PortStyle.accent)
                Text(searching ? "No matching games" : "Your collection starts here")
                    .font(.title2.bold())
                if !searching {
                    Button(action: add) { Label("Add executable", systemImage: "plus") }
                        .buttonStyle(.borderedProminent)
                }
            }.padding(22).frame(maxWidth: .infinity, alignment: .leading).portPanel()
        } else {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 144, maximum: 245), spacing: 12)], alignment: .leading, spacing: 16) {
                ForEach(games) { game in
                    Button { open(game) } label: {
                        Color(white: 0.10).aspectRatio(0.74, contentMode: .fit)
                            .overlay {
                                GeometryReader { box in
                                    LibraryArtwork(entry: game)
                                        .frame(width: box.size.width, height: box.size.height)
                                        .clipped().accessibilityHidden(true)
                                }
                            }
                            .overlay(alignment: .bottomLeading) {
                                LinearGradient(colors: [.clear, .black.opacity(0.94)], startPoint: .top, endPoint: .bottom)
                                    .frame(maxHeight: 104)
                                    .overlay(alignment: .bottomLeading) {
                                        Text(game.title).font(.headline.weight(.heavy)).lineLimit(3)
                                            .foregroundStyle(.white).padding(12)
                                    }
                            }
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .overlay { RoundedRectangle(cornerRadius: 12).strokeBorder(focused == game.id ? PortStyle.signal : Color.primary.opacity(0.12), lineWidth: focused == game.id ? 3 : 1) }
                    }.buttonStyle(PortPress()).accessibilityLabel(game.title).id(game.id)
                }
            }
        }
    }
}
