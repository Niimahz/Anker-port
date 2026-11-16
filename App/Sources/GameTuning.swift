import Foundation

/// User-editable compatibility settings; these are stored locally and do not
/// alter the game's executable or claim to fix unsupported Windows APIs.
struct GameTuning: Codable, Equatable {
    var resolutionWidth: Int = 960
    var resolutionHeight: Int = 540
    var fpsLimit: Int = 30
    var graphicsBackend: GraphicsBackend = .automatic
    var virtualDesktop: Bool = false
    var debugLogging: Bool = false
    var launchArguments: String = ""
    var environmentText: String = ""
    var selectedExecutable: String = ""

    enum GraphicsBackend: String, Codable, CaseIterable, Identifiable {
        case automatic = "Automatic"
        case metal = "Metal"
        case vulkan = "Vulkan"
        var id: String { rawValue }
    }
    var arguments: [String] {
        // Keep quoted arguments together; no shell is invoked.
        // Backslash escapes quotes and spaces; malformed trailing escapes are literal.
        var output: [String] = [], current = ""
        var quote: Character?
        var escaped = false
        for char in launchArguments {
            if escaped { current.append(char); escaped = false; continue }
            if char == "\\" { escaped = true; continue }
            if char == "\"" || char == "'" {
                if quote == char { quote = nil }
                else if quote == nil { quote = char }
                else { current.append(char) }
            } else if char.isWhitespace && quote == nil {
                if !current.isEmpty { output.append(current); current = "" }
            } else { current.append(char) }
        }
        if escaped { current.append("\\") }
        if !current.isEmpty { output.append(current) }
        return output
    }
    var environment: [String: String] {
        var result: [String: String] = [:]
        for line in environmentText.split(whereSeparator: \.isNewline) {
            guard let separator = line.firstIndex(of: "=") else { continue }
            let key = String(line[..<separator]).trimmingCharacters(in: .whitespaces)
            let value = String(line[line.index(after: separator)...])
            guard !key.isEmpty, key.range(of: "^[A-Za-z_][A-Za-z0-9_]*$", options: .regularExpression) != nil else { continue }
            result[key] = value
        }
        return result
    }
}

enum GameTuningStore {
    static func url(for folder: URL) -> URL {
        folder.appendingPathComponent(".anker-compatibility.json")
    }
    static func load(for folder: URL) -> GameTuning {
        guard let data = try? Data(contentsOf: url(for: folder)),
              let tuning = try? JSONDecoder().decode(GameTuning.self, from: data) else {
            return GameTuning()
        }
        return tuning
    }
    static func save(_ tuning: GameTuning, for folder: URL) throws {
        let data = try JSONEncoder().encode(tuning)
        try data.write(to: url(for: folder), options: .atomic)
    }
}
