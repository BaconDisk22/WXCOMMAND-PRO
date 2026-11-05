"""Verify shipped archives from a relocated path while the build checkout is hidden."""
from __future__ import annotations

import os
from pathlib import Path
import plistlib
import subprocess
import tempfile


def verify(bundle: Path, temp: Path) -> None:
    contents = bundle / 'Contents'
    with (contents / 'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    assert info['NSBluetoothAlwaysUsageDescription']
    assert info['NSLocalNetworkUsageDescription']
    executable = contents / 'MacOS' / info['CFBundleExecutable']
    assert os.access(executable, os.X_OK)
    assert list(contents.rglob('Python')), 'Bundled Python runtime missing'
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
    # Every native extension must be Intel-compatible and use only bundled/system dylibs.
    checked = 0
    for file in contents.rglob('*'):
        if not file.is_file() or file.is_symlink():
            continue
        with file.open('rb') as stream:
            magic = stream.read(4)
        if magic not in (bytes.fromhex('cffaedfe'), bytes.fromhex('feedfacf'),
                         bytes.fromhex('cafebabe'), bytes.fromhex('bebafeca')):
            continue
        checked += 1
        arch = subprocess.check_output(['lipo', '-archs', str(file)], text=True).strip()
        assert arch == 'x86_64', (file, arch)
        links = subprocess.check_output(['otool', '-L', str(file)], text=True).splitlines()[1:]
        for link in links:
            dependency = link.strip().split(' (', 1)[0]
            assert dependency.startswith(('@', '/usr/lib/', '/System/Library/')), (file, dependency)
    assert checked > 1, 'No native runtime/extensions found'
    report = temp / 'self-test.txt'
    report.unlink(missing_ok=True)
    home = temp / 'home'
    home.mkdir(exist_ok=True)
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(temp),
           'WXCOMMAND_LOG_DIR': str(temp / 'logs'),
           'WXCOMMAND_SELF_TEST_REPORT': str(report)}
    result = subprocess.run([str(executable), '--self-test'], cwd=temp, env=env, timeout=120)
    log = temp / 'logs/desktop.log'
    if result.returncode or not report.exists():
        raise RuntimeError(log.read_text() if log.exists() else 'Bundle failed before Python started')
    assert report.read_text() == 'standalone self-test passed\n'


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    hidden = root.with_name(root.name + '.packaging-verification-hidden')
    if hidden.exists():
        raise RuntimeError(f'Refusing to overwrite {hidden}')
    with tempfile.TemporaryDirectory(prefix='wxcommand relocated ') as tmp:
        temp = Path(tmp)
        for suffix in ('zip', 'dmg'):
            subprocess.run(['ditto', str(root / f'dist/WXCOMMAND-PRO-macOS-Intel.{suffix}'),
                            str(temp / f'package.{suffix}')], check=True)
        os.chdir(temp)
        root.rename(hidden)
        try:
            extracted = temp / 'zip'
            subprocess.run(['ditto', '-x', '-k', str(temp / 'package.zip'), str(extracted)], check=True)
            verify(extracted / 'WXCOMMAND-PRO.app', temp)
            mount = temp / 'mounted'
            subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(mount),
                            str(temp / 'package.dmg')], check=True)
            try:
                assert (mount / 'Applications').is_symlink()
                assert os.readlink(mount / 'Applications') == '/Applications'
                installed = temp / 'Applications/WXCOMMAND-PRO.app'
                subprocess.run(['ditto', str(mount / installed.name), str(installed)], check=True)
            finally:
                subprocess.run(['hdiutil', 'detach', str(mount)], check=True)
            verify(installed, temp)
        finally:
            hidden.rename(root)
            os.chdir(root)
    print('ZIP and DMG standalone validation passed (no physical radio tests).')


if __name__ == '__main__':
    main()
