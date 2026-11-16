import pathlib
import plistlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "runtime/tools/brand-upstream.py"


class BrandUpstreamTests(unittest.TestCase):
    def test_branding_preserves_runtime_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            app = root / "app/Madeira"
            project = root / "app/Madeira.xcodeproj"
            app.mkdir(parents=True)
            project.mkdir(parents=True)
            info = app / "Info.plist"
            before = {
                "CFBundleDisplayName": "Madeira",
                "CFBundleURLTypes": [{"CFBundleURLSchemes": ["madeira"]}],
                "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
                "NSLocalNetworkUsageDescription": "Old description",
            }
            with info.open("wb") as stream:
                plistlib.dump(before, stream)
            (project / "project.pbxproj").write_text("// test fixture")
            subprocess.run([sys.executable, str(SCRIPT), str(root)], check=True)
            with info.open("rb") as stream:
                after = plistlib.load(stream)
            self.assertEqual(after["CFBundleDisplayName"], "Anker Port")
            self.assertEqual(after["CFBundleURLTypes"], before["CFBundleURLTypes"])
            self.assertEqual(after["CFBundleIdentifier"], before["CFBundleIdentifier"])
            subprocess.run([sys.executable, str(SCRIPT), str(root)], check=True)


if __name__ == "__main__":
    unittest.main()
