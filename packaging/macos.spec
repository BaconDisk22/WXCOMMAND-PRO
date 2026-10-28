"""Intel-only standalone desktop bundle; build with deploy/build_macos_app.py."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
version = next(line.split('"')[1] for line in (root / 'app/__init__.py').read_text().splitlines()
               if line.startswith('__version__'))
datas = [(str(root / 'app/web/templates'), 'app/web/templates'),
         (str(root / 'LICENSE'), '.')]
binaries = []
hiddenimports = collect_submodules('app')
for package in ('meshtastic', 'meshcore', 'bleak', 'serial', 'serial_asyncio',
                'uvicorn', 'zeroconf', 'tzdata', 'certifi'):
    data, binary, hidden = collect_all(package)
    datas += data
    binaries += binary
    hiddenimports += hidden
for package in ('meshtastic', 'meshcore', 'bleak'):
    datas += copy_metadata(package, recursive=True)
a = Analysis([str(root / 'packaging/macos_launcher.py')], pathex=[str(root)],
             datas=datas, binaries=binaries, hiddenimports=hiddenimports,
             excludes=['tkinter', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='WXCOMMAND-PRO',
          console=False, target_arch='x86_64', argv_emulation=False,
          codesign_identity=None, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='WXCOMMAND-PRO', strip=False, upx=False)
app = BUNDLE(coll, name='WXCOMMAND-PRO.app', bundle_identifier='org.wxcommandpro.local',
             version=version, info_plist={
                 'CFBundleDisplayName': 'WXCOMMAND-PRO',
                 'CFBundleShortVersionString': version,
                 'LSUIElement': True,
                 'NSBluetoothAlwaysUsageDescription': 'Connect to Meshtastic and MeshCore Bluetooth radios.',
                 'NSBluetoothPeripheralUsageDescription': 'Discover and connect to your mesh radios.',
                 'NSLocalNetworkUsageDescription': 'Discover and connect to mesh radios over Wi-Fi or TCP.',
             })
