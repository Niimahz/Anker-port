"""Smoke-test Anker's injection into the actual Madeira Swift entry point.

This fixture does not emulate Wine, JIT or iOS; it catches integration drift
before the expensive native IPA build.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATOR = ROOT / "runtime" / "tools" / "integrate-upstream.py"


class MadeiraEntryIntegrationTests(unittest.TestCase):
    def test_overlay_injection_is_idempotent_and_preserves_native_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            swift = root / "app" / "Madeira" / "MadeiraApp.swift"
            swift.parent.mkdir(parents=True)
            native = (
                "import SwiftUI\n"
                "@main struct MadeiraApp: App {\n"
                "    var body: some Scene { WindowGroup {\n"
                "            ContentView()\n"
                "    } }\n"
                "}\n"
            )
            swift.write_text(native)
            first = subprocess.run(
                [sys.executable, str(INTEGRATOR), str(root)],
                capture_output=True, text=True, check=True,
            )
            result = swift.read_text()
            self.assertIn("ANKER_PORT_INTEGRATION_V1", result)
            self.assertEqual(result.count("ANKER_PORT_INTEGRATION_V1"), 1)
            self.assertIn("ContentView()", result)
            self.assertIn("import UniformTypeIdentifiers", result)
            self.assertIn("LibraryModel.inspect(executable)", result)
            self.assertIn("func importGameFolder(", result)
            self.assertIn("JIT", result)
            self.assertIn("Added Anker Downloads", first.stdout)

            second = subprocess.run(
                [sys.executable, str(INTEGRATOR), str(root)],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(swift.read_text(), result)
            self.assertIn("already integrated", second.stdout)

    def test_missing_upstream_entry_fails_without_overwriting_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            swift = root / "app" / "Madeira" / "MadeiraApp.swift"
            swift.parent.mkdir(parents=True)
            original = "import SwiftUI\n// incompatible upstream layout\n"
            swift.write_text(original)
            process = subprocess.run(
                [sys.executable, str(INTEGRATOR), str(root)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(swift.read_text(), original)


if __name__ == "__main__":
    unittest.main()
