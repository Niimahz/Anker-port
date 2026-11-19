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
            }""")
    change("                desktopButton\n                // The library's sections", """                Text("Library").font(.system(.largeTitle, design: .rounded, weight: .heavy)).accessibilityAddTraits(.isHeader)
                desktopButton
                // The library's sections""")
    change("desktop: { AnyView(desktopButton) }", 'desktop: { AnyView(VStack(alignment: .leading, spacing: 14) { Text("Library").font(.largeTitle.bold()); desktopButton }) }')
    change("                    }.padding(4)\n                }\n            }.foregroundStyle(.primary)", """                    }.padding(9).frame(maxWidth: .infinity, alignment: .leading).portPanel()
                }
            }.foregroundStyle(.primary)""")
    source = source.replace(".background(Color(uiColor: .systemGroupedBackground).ignoresSafeArea())", ".background(PortStyle.ground.ignoresSafeArea())")
    change('            .navigationTitle("Game details")', '''            .scrollContentBackground(.hidden).background(PortStyle.ground)
            .tint(PortStyle.accent)
            .navigationTitle("Game details")''')
    change('            .background(pending || configuration.isPressed ? Color(uiColor: .darkGray) : .accentColor,', '''            .background(pending || configuration.isPressed ? Color(uiColor: .darkGray) : Color(red: 0.66, green: 0.22, blue: 0.055),''')
    start = settings.index('        Form {', settings.index('struct SettingsPagesList: View'))
    end = settings.index('    private func summary', start)
    settings = settings[:start] + r'''        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Settings").font(.system(.largeTitle, design: .rounded, weight: .heavy)).accessibilityAddTraits(.isHeader)
                LibraryStatus().padding(16).frame(maxWidth: .infinity, alignment: .leading).portPanel()
                ForEach(Array(SettingsPages.groups.enumerated()), id: \.offset) { _, group in
                    let pages = group.1.filter(\.shown)
                    if !pages.isEmpty {
                        if let title = group.0 { Text(title).font(.headline).accessibilityAddTraits(.isHeader) }
                        VStack(spacing: 0) {
                            ForEach(pages, id: \.self) { page in
                                NavigationLink { SettingsPageView(page: page, startDock: startDock) } label: {
                                    HStack(spacing: 12) {
                                        Image(systemName: page.symbol).frame(width: 32, height: 32)
                                            .foregroundStyle(PortStyle.accent)
                                            .background(PortStyle.accent.opacity(0.1), in: RoundedRectangle(cornerRadius: 9))
                                        Text(page.title).font(.body.weight(.medium))
                                        Spacer()
                                        if let value = summary(page) { Text(value).font(.caption).foregroundStyle(.secondary) }
                                        Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary)
                                    }.padding(.horizontal, 14).padding(.vertical, 9).contentShape(Rectangle())
                                }.buttonStyle(.plain)
                                if page != pages.last { Divider().padding(.leading, 58) }
                            }
                        }.portPanel()
                    }
                }
            }.padding(18).frame(maxWidth: 700).frame(maxWidth: .infinity)
        }.background(PortStyle.ground)
    }

''' + settings[end:]
    settings = settings.replace('Form { content }', 'Form { content }.scrollContentBackground(.hidden).background(PortStyle.ground).tint(PortStyle.accent)')
    onboarding = root / "Onboarding.swift"
    welcome = onboarding.read_text().replace('            .background(Color(uiColor: .systemGroupedBackground).ignoresSafeArea())', '            .background(PortStyle.ground.ignoresSafeArea()).tint(PortStyle.accent)')
    welcome = welcome.replace('                        Text("Step ', '                        PortMark().frame(width: 56, height: 48)\n                        Text("Step ')
    onboarding.write_text(welcome)
    icon = root / "Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"
    icon.write_bytes(Path(__file__).with_name("PortIcon.png").read_bytes())
    pages.write_text(settings.replace(first, credit + "\n" + first))
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
    content.write_text(content.read_text().replace('.navigationTitle("Madeira")', '.navigationTitle("Anker Port")'))
