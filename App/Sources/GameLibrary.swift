import Foundation
import ZIPFoundation
import LibArchive

enum GameLibrary {
    static var documents: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    static var downloads: URL { documents.appendingPathComponent("Downloads", isDirectory: true) }
    static var games: URL { documents.appendingPathComponent("Games", isDirectory: true) }

    static func ensureFolders() throws {
        try FileManager.default.createDirectory(at: downloads, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: games, withIntermediateDirectories: true)
    }
    static func files(in directory: URL) -> [URL] {
        (try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: [.isDirectoryKey], options: [.skipsHiddenFiles]))?
            .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending } ?? []
    }
    static func importArchive(_ source: URL) throws -> URL {
        try ensureFolders()
        let accessed = source.startAccessingSecurityScopedResource()
        defer { if accessed { source.stopAccessingSecurityScopedResource() } }
        let safeName = source.lastPathComponent
        let destination = downloads.appendingPathComponent(UUID().uuidString.prefix(8) + "-" + safeName)
        try FileManager.default.copyItem(at: source, to: destination)
        return destination
    }
    static func extract(_ source: URL) throws -> URL {
        try ensureFolders()
        let name = source.deletingPathExtension().lastPathComponent
        let target = games.appendingPathComponent(name + "-" + UUID().uuidString.prefix(6), isDirectory: true)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        do {
            if source.pathExtension.lowercased() == "zip" {
                try FileManager.default.unzipItem(at: source, to: target)
            } else {
                try ArchiveReader().extract(source, to: target, permissionMode: .normalized)
            }
            return target
        } catch {
            try? FileManager.default.removeItem(at: target)
            throw error
        }
    }
}
