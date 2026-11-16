import SwiftUI
import UIKit

final class StudioAppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     handleEventsForBackgroundURLSession identifier: String,
                     completionHandler: @escaping () -> Void) {
        guard identifier.hasPrefix(GameDownloadManager.backgroundIdentifier) else {
            completionHandler()
            return
        }
        GameDownloadManager.backgroundCompletionHandler = completionHandler
        _ = GameDownloadManager.backgroundManagers[identifier] ?? GameDownloadManager(identifier: identifier)
    }
}

@main
struct AnkerPortStudioApp: App {
    @UIApplicationDelegateAdaptor(StudioAppDelegate.self) var appDelegate
    var body: some Scene {
        WindowGroup { RootView() }
    }
}
