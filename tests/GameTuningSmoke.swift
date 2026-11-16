import Foundation

@main
struct GameTuningSmoke {
    static func main() throws {
        var tuning = GameTuning()
        tuning.launchArguments = #"-windowed -name "My Game" -path C:\\Games\\Demo"#
        let args = tuning.arguments
        precondition(args.contains("My Game"), "Quoted game title was split")
        precondition(args.contains("-windowed"), "Missing first argument")
        tuning.environmentText = "WINEDEBUG=-all\nINVALID KEY=x\nDXVK_HUD=fps"
        precondition(tuning.environment["WINEDEBUG"] == "-all")
        precondition(tuning.environment["DXVK_HUD"] == "fps")
        precondition(tuning.environment["INVALID KEY"] == nil)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        try GameTuningStore.save(tuning, for: directory)
        precondition(GameTuningStore.load(for: directory) == tuning, "Settings did not round-trip")
        print("Game tuning parser and persistence checks passed")
    }
}
