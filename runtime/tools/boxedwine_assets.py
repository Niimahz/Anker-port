"""Prepare the offline Boxedwine Win32 web distribution for the IPA seed."""
import base64
from pathlib import Path

ASSETS = ("boxedwine.zip", "boxedwine-shell.js", "boxedwine.js", "boxedwine.css",
          "browserfs.boxedwine.js", "jszip.min.js", "readme.txt")


def add_runtime(archive, prefix, source):
    source = Path(source)
    for name in ASSETS:
        archive.write(source / name, prefix + name)
    # Pass the WASM bytes directly to Emscripten. Streaming fetch is unavailable
    # for WKURLSchemeHandler resources on some WebKit versions.
    wasm = base64.b64encode((source / "boxedwine.wasm").read_bytes())
    bootstrap = b'Module.wasmBinary = Uint8Array.from(atob("' + wasm + b'"), c => c.charCodeAt(0));\n'
    archive.writestr(prefix + "module.js", bootstrap)
    html = (source / "boxedwine.html").read_text()
    start = html.index("<script>", html.index('src="boxedwine-shell.js"'))
    end = html.index("</body>", start)
    html = html[:start] + """
    <script>
    const configure = setConfiguration;
    setConfiguration = function () {
        configure();
        const path = window.ankerExecutable.split('/');
        Config.Program = path.pop();
        Config.WorkingDir = '/home/username/.wine/dosdevices/d:/' + path.join('/');
        Config.appZipFile = 'game.zip';
    };
    // Custom WebKit origins can restrict storage. Probe the actual writable store
    // before Boxedwine attempts to mount its filesystem.
    try {
        const key = 'anker-boxedwine-write-test';
        localStorage.setItem(key, '1');
        localStorage.removeItem(key);
        Config.storageMode = STORAGE_LOCAL_STORAGE;
    } catch {
        Config.storageMode = STORAGE_MEMORY;
        console.warn('Persistent storage unavailable. Saves last for this session only.');
    }
    document.getElementById('showConsole').checked = false;
    window.addEventListener('error', event => {
        const status = document.getElementById('status');
        status.textContent = event.message || 'Game runtime failed to start.';
        status.parentElement.style.display = '';
    });
    </script>
    <script src="module.js"></script>
    <script src="boxedwine.js"></script>
    """ + html[end:]
    archive.writestr(prefix + "index.html", html)
