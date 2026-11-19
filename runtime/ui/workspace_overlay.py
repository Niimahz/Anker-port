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
