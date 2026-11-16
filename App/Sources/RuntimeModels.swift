import Foundation

enum RuntimeKind: String, Codable, CaseIterable, Identifiable {
    case madeira = "Madeira"
    case playport = "PlayPort"
    var id: String { rawValue }
}

enum TestStatus: String, Codable {
    case untested, launched, playable, failed
}

struct CompatibilityProfile: Codable {
    let schemaVersion: Int
    let gameName: String
    let executable: String
    let architecture: String
    let runtime: RuntimeKind
    var status: TestStatus
    var launchArguments: [String]
    var environment: [String: String]
    var notes: [String]
}

protocol RuntimeAdapter {
    var kind: RuntimeKind { get }
    func validate(profile: CompatibilityProfile) -> [String]
}

struct MadeiraAdapter: RuntimeAdapter {
    let kind: RuntimeKind = .madeira
    func validate(profile: CompatibilityProfile) -> [String] {
        ["Madeira runtime not integrated", "JIT and device compatibility require testing"]
    }
}

struct PlayPortAdapter: RuntimeAdapter {
    let kind: RuntimeKind = .playport
    func validate(profile: CompatibilityProfile) -> [String] {
        ["PlayPort runtime not integrated", "Source-level compatibility not yet verified"]
    }
}
