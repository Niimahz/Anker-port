"""Host-side integration smoke tests; no iOS runtime execution is implied."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATOR = ROOT / "runtime/tools/integrate-upstream.py"


class AnkerIntegrationSmokeTests(unittest.TestCase):
    def test_injection_idempotence_and_runtime_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "app/Madeira"
            app.mkdir(parents=True)
            target = app / "MadeiraApp.swift"
            target.write_text("import SwiftUI\nstruct MadeiraApp {\n            ContentView()\n}\n")
            def integrate():
                return subprocess.run(
                    [sys.executable, str(INTEGRATOR), temporary],
                    capture_output=True, text=True, check=True,
                )
            integrate()
            injected = target.read_text()
            self.assertEqual(injected.count("// ANKER_PORT_INTEGRATION_V1"), 1)
            self.assertIn("import UniformTypeIdentifiers", injected)
            self.assertIn("LibraryModel.inspect(executable)", injected)
            self.assertIn("library.save(entry)", injected)
            self.assertIn("func importGameFolder(_ source: URL)", injected)
            self.assertIn("FileManager.default.copyItem(at: source, to: destination)", injected)
            self.assertIn("try addToLibrary(executable)", injected)
            self.assertIn("JITCoordinator.shared", injected)
            self.assertIn("JIT execution verified: No (status snapshot only)", injected)
            self.assertIn("launch integration is pending", injected)
            # Preflight must reject overlap before traversing any source entries.
            folder = injected.split("func importGameFolder(_ source: URL)", 1)[1]
            self.assertLess(folder.index("sourcePath != importPath"),
                            folder.index("FileManager.default.enumerator("))
            self.assertLess(folder.index("FileManager.default.enumerator("),
                            folder.index("FileManager.default.copyItem(at: source, to: destination)"))
            integrate()
            self.assertEqual(target.read_text(), injected)

    def test_upstream_entry_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "app/Madeira"
            app.mkdir(parents=True)
            (app / "MadeiraApp.swift").write_text("import SwiftUI\n")
            result = subprocess.run(
                [sys.executable, str(INTEGRATOR), temporary],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("upstream entry point changed", result.stderr)


if __name__ == "__main__":
    unittest.main()
