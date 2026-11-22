"""Install the Anker workspace into the pinned native library frontend."""
import json
from pathlib import Path


def install(root: Path):
    path = root / "Library.swift"
    source = path.read_text()

    def change(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("Unexpected library template: " + old)
        source = source.replace(old, new)

    change("@State private var tab = 0", "@State private var tab = 4\n    @StateObject private var web = AnkerWebSession()")
    change('static let title = "Madeira"', 'static let title = "Anker Port"')
    change('            // The card layouts:', '''            AnkerHome(library: model, play: play, select: switchTab)
                .tabItem { Label("Home", systemImage: "house.fill") }.tag(4)
            // The card layouts:''')
    change('Image(systemName: "square.grid.2x2.fill").accessibilityLabel("Library")', 'Label("Library", systemImage: "square.grid.2x2.fill")')
    change('            settingsTab\n', '''            AnkerNativeDownloads()
                .tabItem { Label("Downloads", systemImage: "arrow.down.circle.fill") }.tag(2)
            AnkerBrowser(session: web)
                .tabItem { Label("Browser", systemImage: "safari.fill") }.tag(3)
            settingsTab
''')
    change('Image(systemName: "gearshape.fill").accessibilityLabel("Settings")', 'Label("Settings", systemImage: "gearshape.fill")')
    change('.background(LibraryNavSearch', '.tint(.teal)\n        .background { if tab == 0 || tab == 1 { LibraryNavSearch')
    change('.frame(width: 0, height: 0))\n        // Each tab', '.frame(width: 0, height: 0) } }\n        // Each tab')
    change('else { settingsToolbar }', 'else if tab == 1 { settingsToolbar }')
    change('switchTab(to: 1 - tab)', 'switchTab(to: [4: 0, 0: 2, 2: 3, 3: 1, 1: 4][tab] ?? 4)')
    change('settingsShow("credits", "thanks",', 'settingsShow("credits", "Nima HZ", "Niimahz", "thanks",')
    change('if SettingsPages.enabled, settingsSearch.trimmingCharacters', 'if settingsSearch.trimmingCharacters')
    pages = root / "SettingsPages.swift"
    settings = pages.read_text()
    first = '            MadeiraCredit(name: "Will Faust"'
    if settings.count(first) != 1:
        raise ValueError("Unexpected Credits layout")
    credit = '            MadeiraCredit(name: "Nima HZ", handle: "Niimahz", role: "Created Anker Port")'
    # Hide the system bar in each tab so a sheet or a pushed screen keeps its own controls.
    source = source.replace(".tabItem {", ".toolbar(.hidden, for: .tabBar)\n                .tabItem {")
    change("        .tint(.teal)", """        .safeAreaInset(edge: .bottom, spacing: 0) { PortDock(tab: tab, select: switchTab) }
        .tint(PortStyle.accent)""")
    change("            LibraryLargeTitle()", """            ToolbarItem(placement: .topBarLeading) {
                HStack(spacing: 7) {
                    PortMark().frame(width: 30, height: 29)
                    Text("Anker Port").font(.system(.headline, design: .rounded, weight: .heavy))
                }.accessibilityElement(children: .combine)
            }
            if tab == 4, let supportURL = URL(string: "https://buymeacoffee.com/Niimahz") {
                ToolbarItem(placement: .topBarTrailing) {
                    Link(destination: supportURL) {
                        Image(systemName: "cup.and.saucer.fill")
                            .resizable().scaledToFit()
                            .foregroundStyle(PortStyle.accent)
                            .frame(width: 30, height: 29)
                    }
                    .accessibilityLabel("Buy Me a Coffee")
                }
            }""")
    change('@State private var search = ""', '@State private var search = ""\n    @State private var showsSources = false')
    change('Group { if LibraryGridArm.zoomable(setting: zoomableGrid, layout: layout)', 'Group { if showsSources && LibraryGridArm.zoomable(setting: zoomableGrid, layout: layout)')
    change('        guard group != "platform" else', '        if !showsSources { return collectionGames }\n        guard group != "platform" else')
    change('    private var library: some View {', r'''    private var collectionGames: [LibraryEntry] {
        let games = model.entries.filter { $0.desktop != true && $0.listedInLibrary && (search.isEmpty || $0.title.localizedCaseInsensitiveContains(search)) }
        if sort == "added" { return Array(games.reversed()) }
        return games.sorted {
            if sort == "played", $0.lastPlayed != $1.lastPlayed { return ($0.lastPlayed ?? .distantPast) > ($1.lastPlayed ?? .distantPast) }
            if sort == "size", $0.folderBytes != $1.folderBytes { return ($0.folderBytes ?? -1) > ($1.folderBytes ?? -1) }
            return $0.title.localizedStandardCompare($1.title) == .orderedAscending
        }
    }
    private var collectionHeader: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("Library").font(.system(.largeTitle, design: .serif, weight: .bold))
                Spacer()
                if !showsSources {
                    Text(String(collectionGames.count)).font(.title.monospacedDigit()).foregroundStyle(.secondary)
                        .accessibilityLabel("Games: " + String(collectionGames.count))
                }
            }
            HStack(spacing: 8) {
                ForEach([false, true], id: \.self) { sources in
                    Button { showsSources = sources } label: {
                        Text(sources ? "Sources" : "Collection").font(.headline)
                            .padding(.horizontal, 14).frame(minHeight: 44)
                            .foregroundStyle(showsSources == sources ? Color.black : Color.primary)
                            .background(showsSources == sources ? PortStyle.signal : PortStyle.panel, in: Capsule())
                    }.buttonStyle(PortPress()).accessibilityAddTraits(showsSources == sources ? .isSelected : [])
                }
            }
        }
    }
    private var library: some View {''')
    change('                if !storeTabs.isEmpty { LibraryStoreTabBar(tabs: storeTabs, selection: $storeTab) }\n                desktopButton', '''                collectionHeader
                if !showsSources {
                    PortCollectionWall(games: collectionGames, searching: !search.isEmpty, focused: controller.connected ? focused : nil,
                                       open: { selected = $0 }, add: { browser = true })
                    desktopButton
                } else {
                if !storeTabs.isEmpty { LibraryStoreTabBar(tabs: storeTabs, selection: $storeTab) }
                desktopButton''')
    change('            }\n            // Ambient light behind the grid cards', '                }\n            }\n            // Ambient light behind the grid cards')
    change("desktop: { AnyView(desktopButton) }", 'desktop: { AnyView(VStack(alignment: .leading, spacing: 14) { collectionHeader; desktopButton }) }')
    change('            } label: { Label("Library options"', '''                if !showsSources { Button("Browse sources and layouts") { showsSources = true } }
            } label: { Label("Library options"''')
    change('                if zoomableGrid {\n                    // The new grid', '                if showsSources {\n                if zoomableGrid {\n                    // The new grid')
    change('                Picker("Sort by", selection: $sort)', '                }\n                Picker("Sort by", selection: $sort)')
    source = source.replace(".background(Color(uiColor: .systemGroupedBackground).ignoresSafeArea())", ".background(PortStyle.ground.ignoresSafeArea())")
    change('            .navigationTitle("Game details")', '''            .scrollContentBackground(.hidden).background(PortStyle.ground)
            .tint(PortStyle.accent)
            .navigationTitle("Game details")''')
    change('            .background(pending || configuration.isPressed ? Color(uiColor: .darkGray) : .accentColor,', '''            .background(pending || configuration.isPressed ? Color(uiColor: .darkGray) : Color(red: 0.66, green: 0.22, blue: 0.055),''')
    start = settings.index('    var body: some View {', settings.index('struct SettingsPagesList: View'))
    end = settings.index('    private func summary', start)
    settings = settings[:start] + r'''    @State private var category = 0
    private let groups = SettingsPages.groups
    private let names = ["Stores", "Gameplay", "Device", "App"]
    private let symbols = ["bag", "gamecontroller", "cpu", "switch.2"]
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Control room").font(.system(.largeTitle, design: .serif, weight: .bold))
                    .accessibilityAddTraits(.isHeader)
                LibraryStatus().frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16).portPanel()
                ScrollView(.horizontal) {
                    HStack(spacing: 8) {
                        ForEach(groups.indices, id: \.self) { i in
                            if groups[i].1.contains(where: { $0.shown }) {
                                Button { category = i } label: {
                                    Label(names[i], systemImage: symbols[i]).font(.subheadline.bold())
                                        .fixedSize().padding(.horizontal, 13).frame(minHeight: 44)
                                        .foregroundStyle(category == i ? Color.black : Color.primary)
                                        .background(category == i ? PortStyle.signal : PortStyle.panel, in: Capsule())
                                }.buttonStyle(PortPress()).accessibilityAddTraits(category == i ? .isSelected : [])
                            }
                        }
                    }
                }.scrollIndicators(.hidden)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 142, maximum: 290), spacing: 10)], spacing: 10) {
                    ForEach(groups[category].1.filter(\.shown), id: \.self) { page in
                        NavigationLink { SettingsPageView(page: page, startDock: startDock) } label: {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack { Image(systemName: page.symbol).font(.title2).foregroundStyle(PortStyle.accent)
                                    Spacer(); Image(systemName: "arrow.up.right").font(.caption).foregroundStyle(.secondary) }
                                Spacer(minLength: 8)
                                Text(page.title).font(.headline)
                                if let value = summary(page) { Text(value).font(.caption).foregroundStyle(.secondary) }
                            }.padding(15).frame(maxWidth: .infinity, minHeight: 116, alignment: .topLeading).portPanel()
                        }.buttonStyle(PortPress())
                    }
                }
            }.padding(18).frame(maxWidth: 740).frame(maxWidth: .infinity)
        }.background(PortStyle.ground)
        .onAppear {
            if !groups[category].1.contains(where: { $0.shown }) {
                category = groups.firstIndex(where: { $0.1.contains(where: { $0.shown }) }) ?? 0
            }
        }
    }

''' + settings[end:]
    # Keep native controls and their modal presenters in every individual settings page.
    settings = settings.replace('Form { content }', '''Form {
                Section {
                    Label(page.title, systemImage: page.symbol)
                        .font(.system(.title2, design: .serif, weight: .bold))
                        .padding(.vertical, 8)
                }.listRowBackground(PortStyle.panel)
                content
            }.scrollContentBackground(.hidden).background(PortStyle.ground).tint(PortStyle.accent)''').replace('.navigationTitle(page.title)', '.navigationTitle("Settings")')
    onboarding = root / "Onboarding.swift"
    welcome = onboarding.read_text().replace('            .background(Color(uiColor: .systemGroupedBackground).ignoresSafeArea())', '            .background(PortStyle.ground.ignoresSafeArea()).tint(PortStyle.accent)')
    welcome = welcome.replace('                        Text("Step ', '                        PortMark().frame(width: 56, height: 48)\n                        Text("Step ')
    onboarding.write_text(welcome)
    icon = root / "Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"
    icon.write_bytes(Path(__file__).with_name("PortIcon.png").read_bytes())
    pages.write_text(settings.replace(first, credit + "\n" + first))
    change("                // A Play error sits under Play.", "                PortExportSection(entry: entry)\n                // A Play error sits under Play.")
    path.write_text(source)

    # Keep lookup keys and the on-disk format stable. SwiftUI resolves display
    # strings through the catalog; the explicit fallback also covers dynamic L calls.
    catalog = root / "Localizable.xcstrings"
    data = json.loads(catalog.read_text())
    for key, item in data["strings"].items():
        if "Madeira" in key and "copyright" not in key.lower() and "github.com" not in key:
            loc = item.setdefault("localizations", {})
            loc.setdefault("en", {"stringUnit": {"state": "translated", "value": key}})
            for locale in loc.values():
                unit = locale.get("stringUnit")
                if unit:
                    unit["value"] = unit["value"].replace("Madeira", "Anker Port")
    catalog.write_text(json.dumps(data, ensure_ascii=False))
    content = root / "ContentView.swift"
    view = content.read_text()
    marker = "                } else if library.enabled {"
    if view.count(marker) != 1:
        raise ValueError("Unexpected game launch entry point")
    view = view.replace("if library.enabled && library.current != nil {", "if (library.enabled || PortGamePackage.standalone) && library.current != nil {")
    view = view.replace(marker, "                } else if PortGamePackage.standalone {\n                    PortSingleGame(play: launchLibraryEntry)\n" + marker)
    content.write_text(view.replace('.navigationTitle("Madeira")', '.navigationTitle("Anker Port")'))
