import pathlib
import plistlib
import subprocess
import sys
import tempfile
import unittest
import zipfile


class VerifyIPATests(unittest.TestCase):
    def test_rejects_text_in_place_of_native_executable(self):
        verifier = pathlib.Path(__file__).resolve().parents[1] / "runtime/tools/verify-ipa.py"
        with tempfile.TemporaryDirectory() as folder:
            ipa = pathlib.Path(folder) / "invalid.ipa"
            app = "Payload/Madeira.app/"
            with zipfile.ZipFile(ipa, "w") as archive:
                archive.writestr(app + "Info.plist", plistlib.dumps({
                    "CFBundleDisplayName": "Anker Port", "CFBundleExecutable": "Madeira"
                }))
                archive.writestr(app + "Madeira", b"x" * 8192)
                archive.writestr(app + "prefix-template.tar.gz", b"placeholder")
                archive.writestr(app + "arm64ec-windows/xtajit64.dll", b"MZ")
                archive.writestr(app + "x86_64-vcruntime/vcruntime140.dll", b"MZ")
            result = subprocess.run([sys.executable, verifier, ipa], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ARM64 Mach-O", result.stderr)
            self.assertFalse(ipa.with_suffix(".manifest.json").exists())
