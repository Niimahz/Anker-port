import Foundation

/// Runtime integration boundary. The native Wine/FEX libraries must be compiled into
/// this app; a Windows .exe cannot be started using Process or UIApplication.open.
enum RuntimeLaunchError: LocalizedError {
    case unavailable
    case noExecutable
    case outsideLibrary
    case invalidArchitecture
    case jitRequired
    var errorDescription: String? {
        switch self {
        case .unavailable: return "The in-process Windows runtime is not linked into this build."
        case .noExecutable: return "The selected Windows executable does not exist."
        case .outsideLibrary: return "The executable must be inside the imported game library."
        case .invalidArchitecture: return "The selected file is not a supported Windows PE executable."
        case .jitRequired: return "A debugger-authorized JIT pool is required before Windows code can run."
        }
    }
}

struct RuntimeLaunchRequest {
    let gameFolder: URL
    let executable: URL
    let arguments: [String]
    let environment: [String: String]
}

struct RuntimeLaunchResult {
    let started: Bool
    let diagnostic: String
}

enum RuntimeLauncher {
    /// This validation is deliberately independent of the Wine runtime.
    static func preflight(_ request: RuntimeLaunchRequest) throws {
        let root = GameLibrary.games.resolvingSymlinksInPath().standardizedFileURL
        let game = request.gameFolder.resolvingSymlinksInPath().standardizedFileURL
        let executable = request.executable.resolvingSymlinksInPath().standardizedFileURL
        guard game.path.hasPrefix(root.path + "/"),
              executable.path.hasPrefix(game.path + "/") else {
            throw RuntimeLaunchError.outsideLibrary
        }
        guard FileManager.default.fileExists(atPath: executable.path) else {
            throw RuntimeLaunchError.noExecutable
        }
        let info = GameAnalyzer.inspectPE(url: executable, relative: executable.lastPathComponent)
        guard info.error == nil, ["x86", "x64"].contains(info.architecture) else {
            throw RuntimeLaunchError.invalidArchitecture
        }
    }

    static var isAvailable: Bool {
        // Be explicit: the source-level ABI adapter is not a compiled Wine/FEX runtime.
        false
    }

    static func launch(_ request: RuntimeLaunchRequest) throws -> RuntimeLaunchResult {
        try preflight(request)
        throw RuntimeLaunchError.unavailable
    }
}
