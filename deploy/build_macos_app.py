"""Build a standalone x86_64 .app, ZIP and drag-and-drop DMG on Intel macOS."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


def build(root: Path) -> Path:
    if sys.platform != 'darwin' or platform.machine() != 'x86_64':
        raise RuntimeError('Build with x86_64 Python on an Intel macOS runner')
    root = root.resolve()
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(root / 'build/pyinstaller-cache'))
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    str(root / 'packaging/macos.spec')], cwd=root, env=env, check=True)
    bundle = root / 'dist/WXCOMMAND-PRO.app'
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
    # ditto preserves the bundle's symlinks, permissions and root directory.
    archive = root / 'dist/WXCOMMAND-PRO-macOS-Intel.zip'
    archive.unlink(missing_ok=True)
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(bundle), str(archive)], check=True)
    dmg = root / 'dist/WXCOMMAND-PRO-macOS-Intel.dmg'
    with tempfile.TemporaryDirectory(prefix='wxcommand-dmg-') as temp:
        staging = Path(temp)
        subprocess.run(['ditto', str(bundle), str(staging / bundle.name)], check=True)
        (staging / 'Applications').symlink_to('/Applications')
        (staging / 'Install.txt').write_text(
            'Drag WXCOMMAND-PRO.app to Applications, then open it.\n'
            'Use the WX menu-bar menu to open the dashboard or quit.\n'
            'This prerelease is not Developer ID signed or notarized.\n'
            'Radio hardware and target macOS compatibility require separate verification.\n')
        subprocess.run(['hdiutil', 'create', '-ov', '-volname', 'WXCOMMAND-PRO',
                        '-srcfolder', temp, '-format', 'UDZO', str(dmg)], check=True)
    subprocess.run(['hdiutil', 'verify', str(dmg)], check=True)
    return bundle


if __name__ == '__main__':
    print(build(Path(__file__).resolve().parent.parent))
