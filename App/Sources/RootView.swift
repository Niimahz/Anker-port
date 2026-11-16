import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            NavigationStack { LibraryScreen() }
                .tabItem { Label("Library", systemImage: "square.stack") }
            NavigationStack { DownloadScreen() }
                .tabItem { Label("Downloads", systemImage: "arrow.down.circle") }
            StudioView()
                .tabItem { Label("Analyzer", systemImage: "doc.text.magnifyingglass") }
        }
    }
}
