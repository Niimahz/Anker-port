import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "runtime/tools/integrate-upstream.py"


class IntegrationTests(unittest.TestCase):
    def test_injection_is_idempotent_and_preserves_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "app/Madeira/MadeiraApp.swift"
            source.parent.mkdir(parents=True)
            source.write_text("import SwiftUI\nstruct MadeiraApp {\n    var body: some Scene {\n        WindowGroup {\n            ContentView()\n                .onAppear { runWineFullSequence() }\n        }\n    }\n}\n")
            subprocess.run([sys.executable, str(SCRIPT), tmp], check=True)
            first = source.read_text()
            self.assertIn("runWineFullSequence()", first)
            self.assertIn("AnkerNativeDownloads", first)
            self.assertNotIn("}\n                        .foregroundStyle(.secondary)", first)
            self.assertIn("session.download(from: url)", first)
            self.assertIn("LibraryModel.inspect(executable)", first)
            self.assertIn("library.save(entry)", first)
            self.assertIn("LibraryModel.drive", first)
            self.assertIn("func importGameFolder(_ source: URL)", first)
            self.assertIn("startAccessingSecurityScopedResource()", first)
            self.assertIn("FileManager.default.copyItem(at: source, to: destination)", first)
            self.assertIn("allowedContentTypes: [.folder]", first)
            self.assertNotIn("func runWineFullSequence", first)
            self.assertNotIn("private struct LibraryEntry", first)
            subprocess.run([sys.executable, str(SCRIPT), tmp], check=True)
            self.assertEqual(first, source.read_text())


if __name__ == "__main__":
    unittest.main()
