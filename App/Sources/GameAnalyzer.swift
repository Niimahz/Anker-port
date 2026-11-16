import Foundation

struct PEInfo: Codable, Identifiable {
    var id: String { path }
    let path: String
    let architecture: String
    let format: String
    let importedDLLs: [String]
    let error: String?
}

struct GameReport: Codable {
    let name: String
    let scannedAt: Date
    let executables: [PEInfo]
    let scripts: [String]
    let warnings: [String]
}

enum GameAnalyzer {
    static func analyze(folder: URL) throws -> GameReport {
        let keys: Set<URLResourceKey> = [.isRegularFileKey, .isSymbolicLinkKey]
        guard let walker = FileManager.default.enumerator(
            at: folder, includingPropertiesForKeys: Array(keys), options: [.skipsHiddenFiles]
        ) else { throw CocoaError(.fileReadUnknown) }
        var binaries = [PEInfo]()
        var scripts = [String]()
        var warnings = [String]()
        var count = 0
        for case let url as URL in walker {
            count += 1
            if count > 100_000 { warnings.append("Scan limited to 100,000 items"); break }
            let props = try? url.resourceValues(forKeys: keys)
            if props?.isSymbolicLink == true { walker.skipDescendants(); continue }
            guard props?.isRegularFile == true else { continue }
            let relative = String(url.path.dropFirst(folder.path.count))
                .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            switch url.pathExtension.lowercased() {
            case "exe", "dll": binaries.append(inspectPE(url: url, relative: relative))
            case "bat", "cmd": scripts.append(relative)
            default: break
            }
        }
        if binaries.isEmpty { warnings.append("No EXE or DLL found") }
        return GameReport(name: folder.lastPathComponent, scannedAt: Date(),
                          executables: binaries, scripts: scripts, warnings: warnings)
    }

    static func inspectPE(url: URL, relative: String) -> PEInfo {
        do {
            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            let data = try handle.read(upToCount: 16 * 1024 * 1024) ?? Data()
            func u16(_ p: Int) -> Int? {
                guard p >= 0 && p + 2 <= data.count else { return nil }
                return Int(data[p]) | (Int(data[p + 1]) << 8)
            }
            func u32(_ p: Int) -> Int? {
                guard p >= 0 && p + 4 <= data.count else { return nil }
                return (0..<4).reduce(0) { $0 | (Int(data[p + $1]) << ($1 * 8)) }
            }
            guard u16(0) == 0x5A4D, let pe = u32(0x3C),
                  pe >= 0x40, pe < 1_000_000, u32(pe) == 0x00004550,
                  let machine = u16(pe + 4), let sectionCount = u16(pe + 6),
                  let optionalSize = u16(pe + 20), let magic = u16(pe + 24)
            else { throw CocoaError(.fileReadCorruptFile) }
            let architecture: String
            switch machine {
            case 0x14c: architecture = "x86"
            case 0x8664: architecture = "x64"
            case 0xaa64: architecture = "ARM64"
            default: architecture = String(format: "Unknown (0x%04X)", machine)
            }
            let format = magic == 0x20B ? "PE32+" : magic == 0x10B ? "PE32" : "Unknown"
            let opt = pe + 24
            let directoryOffset = magic == 0x20B ? 112 : 96
            var imports: [String] = []
            if let importRVA = u32(opt + directoryOffset + 8), importRVA != 0,
               sectionCount <= 96, optionalSize >= directoryOffset + 16 {
                let sections = opt + optionalSize
                func fileOffset(_ rva: Int) -> Int? {
                    for i in 0..<sectionCount {
                        let p = sections + i * 40
                        guard let virtualSize = u32(p + 8), let va = u32(p + 12),
                              let rawSize = u32(p + 16), let rawPointer = u32(p + 20) else { continue }
                        let size = max(virtualSize, rawSize)
                        if rva >= va && rva - va < size {
                            let offset = rawPointer + rva - va
                            return offset < data.count ? offset : nil
                        }
                    }
                    return nil
                }
                if let table = fileOffset(importRVA) {
                    for i in 0..<256 {
                        let p = table + i * 20
                        guard let nameRVA = u32(p + 12), let firstThunk = u32(p + 16) else { break }
                        if nameRVA == 0 && firstThunk == 0 { break }
                        guard let start = fileOffset(nameRVA) else { continue }
                        let end = min(start + 260, data.count)
                        let bytes = data[start..<end].prefix(while: { $0 != 0 })
                        if let name = String(bytes: bytes, encoding: .ascii), !name.isEmpty {
                            imports.append(name)
                        }
                    }
                }
            }
            return PEInfo(path: relative, architecture: architecture, format: format,
                          importedDLLs: Array(Set(imports)).sorted(), error: nil)
        } catch {
            return PEInfo(path: relative, architecture: "Unknown", format: "Unknown",
                          importedDLLs: [], error: "Invalid, truncated or unreadable PE file")
        }
    }
}
