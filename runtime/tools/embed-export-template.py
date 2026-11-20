"""Add a pristine, non-recursive runtime template to the downloadable Anker IPA."""
import argparse
import plistlib
import shutil
import tempfile
from boxedwine_assets import add_runtime
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

parser = argparse.ArgumentParser()
parser.add_argument("runtime", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--boxedwine", type=Path, required=True)
args = parser.parse_args()
with ZipFile(args.runtime) as archive:
    infos = [name for name in archive.namelist() if name.startswith("Payload/") and name.endswith(".app/Info.plist") and name.count("/") == 2]
    if len(infos) != 1:
        raise ValueError("Expected exactly one iOS app")
    prefix = infos[0].removesuffix("Info.plist")
    info = archive.read(infos[0])
    if prefix + "PortSeed.bin" in archive.namelist():
        raise ValueError("Refusing to embed a recursive template")
shutil.copyfile(args.runtime, args.output)
with tempfile.TemporaryDirectory() as work:
    seed = Path(work) / "seed.ipa"
    shutil.copyfile(args.runtime, seed)
    with ZipFile(seed, "a", allowZip64=True) as archive:
        add_runtime(archive, prefix + "PortBoxedWine/", args.boxedwine)
    with ZipFile(args.output, "a", allowZip64=True) as archive:
        archive.write(seed, prefix + "PortSeed.bin", compress_type=ZIP_STORED)
        archive.writestr(prefix + "PortSeed.plist", plistlib.dumps({"prefix": prefix, "info": plistlib.loads(info)}))
