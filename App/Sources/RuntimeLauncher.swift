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

    /// A linked host must validate JIT mappings; iOS version alone is not evidence.
    static func jitDiagnostic(nativeHostLinked: Bool, poolVerified: Bool) -> String {
        if !nativeHostLinked { return "JIT not checked: native Wine/FEX host is not linked." }
        if !poolVerified { return "JIT unavailable: executable RX/RW pool not verified by native host." }
        return "JIT pool reported by native host; device execution remains untested."
    }

    @discardableResult
    static func saveFailure(stage: String, executable: URL, detail: String) -> URL? {
        let directory = GameLibrary.documents.appendingPathComponent("RuntimeReports", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let file = directory.appendingPathComponent(UUID().uuidString + ".txt")
            let safeDetail = detail.replacingOccurrences(of: "\n", with: " ")
            let report = "timestamp=\(ISO8601DateFormatter().string(from: Date()))\nstage=\(stage)\nexecutable=\(executable.lastPathComponent)\ndetail=\(safeDetail)\n"
            try report.write(to: file, atomically: true, encoding: .utf8)
            return file
        } catch { return nil }
    }

    static func diagnose(_ request: RuntimeLaunchRequest) -> String {
        do {
            try preflight(request)
            let detail = "PE preflight passed. " + jitDiagnostic(nativeHostLinked: isAvailable, poolVerified: false)
            saveFailure(stage: "preflight", executable: request.executable, detail: detail)
            return detail
        } catch {
            saveFailure(stage: "preflight-failed", executable: request.executable, detail: error.localizedDescription)
            return error.localizedDescription
        }
    }
    /// This validation is deliberately independent of the Wine runtime.
    static func preflight(_ request: RuntimeLaunchRequest) throws {
        let root = GameLibrary.games.resolvingSymlinksInPath().standardizedFileURL
        let game = request.gameFolder.resolvingSymlinksInPath().standardizedFileURL
        let executable = request.executable.resolvingSymlinksInPath().standardizedFileURL
        guard game.path.hasPrefix(root.path + "/"),
              executable.path.hasPrefix(game.path + "/") else {
            throw RuntimeLaunchError.outsideLibrary
        }
        let values = try? executable.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        guard values?.isRegularFile == true, values?.isSymbolicLink != true else {
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
        do {
            try preflight(request)
            throw RuntimeLaunchError.unavailable
        } catch {
            saveFailure(stage: "launch-failed", executable: request.executable, detail: error.localizedDescription)
            throw error
        }
    }
}
