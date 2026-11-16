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
            self.assertIn("URLSession.shared.download", first)
            subprocess.run([sys.executable, str(SCRIPT), tmp], check=True)
            self.assertEqual(first, source.read_text())


if __name__ == "__main__":
    unittest.main()
