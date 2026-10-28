"""Finder launcher and menu-bar lifecycle for the standalone Mac build."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import socket
import sys
import threading
import time
import webbrowser


def reserve_socket(host: str, port: int) -> socket.socket:
    """Bind before opening a browser, so a foreign service is never shown."""
    family = socket.AF_INET6 if ':' in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        # Quit-then-reopen leaves TIME_WAIT connections; a live listener still conflicts.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(128)
        return sock
    except BaseException:
        sock.close()
        raise


def self_test() -> None:
    """Exercise frozen dependencies and real HTTP without radios or pollers."""
    import importlib
    import tempfile
    import httpx
    import uvicorn
    from zoneinfo import ZoneInfo
    from app.main import create_app

    for module in ('meshtastic.tcp_interface', 'meshtastic.serial_interface',
                   'meshtastic.ble_interface', 'meshcore', 'bleak.backends.corebluetooth',
                   'serial.tools.list_ports', 'zeroconf', 'app.poller', 'app.ipaws',
                   'AppKit', 'Foundation', 'certifi'):
        importlib.import_module(module)
    import certifi
    assert Path(certifi.where()).is_file()
    ZoneInfo('America/New_York')
    from app.web.routes import TEMPLATES
    env = TEMPLATES.env
    for name in env.list_templates():
        env.get_template(name)
    # An isolated database path prevents middleware from touching the user's data.
    with tempfile.TemporaryDirectory() as temp:
        os.environ['MESH_WX_DB'] = str(Path(temp) / 'test.db')
        os.environ['MESH_WX_HOST'] = '127.0.0.1'
        sock = reserve_socket('127.0.0.1', 0)
        server = uvicorn.Server(uvicorn.Config(create_app(), lifespan='off',
                                             log_config=None, loop='asyncio'))
        worker = threading.Thread(target=server.run, kwargs={'sockets': [sock]})
        worker.start()
        try:
            deadline = time.monotonic() + 30
            while not server.started:
                if not worker.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError('Packaged HTTP server failed to start')
                time.sleep(.05)
            with httpx.Client(base_url=f'http://127.0.0.1:{sock.getsockname()[1]}', trust_env=False) as client:
                assert client.get('/healthz').text == 'ok'
                demo = client.get('/demo')
                assert demo.status_code == 200 and 'html' in demo.text.lower()
                preview = client.post('/api/ux/preview', json={'message': 'Packaging check'})
                assert preview.status_code == 200 and preview.json()['transmitted'] is False
        finally:
            server.should_exit = True
            worker.join(15)
            sock.close()
            if worker.is_alive():
                raise RuntimeError('Packaged HTTP server did not stop')
    report = os.environ.get('WXCOMMAND_SELF_TEST_REPORT')
    if report:
        Path(report).write_text('standalone self-test passed\n')


def run_desktop() -> None:
    import AppKit
    from Foundation import NSObject, NSTimer
    import uvicorn
    from app.config import load_bootstrap
    from app.main import app

    cfg = load_bootstrap()
    sock = reserve_socket(cfg.http_host, cfg.http_port)
    browse_host = '127.0.0.1' if cfg.http_host in ('0.0.0.0', '::') else cfg.http_host
    if ':' in browse_host:
        browse_host = f'[{browse_host}]'
    url = f'http://{browse_host}:{cfg.http_port}/operator'
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, loop='asyncio'))
    worker = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    application = AppKit.NSApplication.sharedApplication()
    application.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    class DesktopDelegate(NSObject):
        def openDashboard_(self, sender):
            if server.started:
                webbrowser.open(url)

        def quit_(self, sender):
            application.terminate_(None)

        def applicationShouldTerminate_(self, sender):
            server.should_exit = True
            worker.join(15)
            return AppKit.NSTerminateNow

        def checkStartup_(self, timer):
            if server.started:
                timer.invalidate()
                self.openDashboard_(None)
            elif not worker.is_alive() or time.monotonic() > self.deadline:
                timer.invalidate()
                alert = AppKit.NSAlert.alloc().init()
                alert.setMessageText_('WXCOMMAND-PRO could not start')
                alert.setInformativeText_('See ~/Library/Logs/WXCOMMAND-PRO/desktop.log for details.')
                alert.runModal()
                application.terminate_(None)

    delegate = DesktopDelegate.alloc().init()
    delegate.deadline = time.monotonic() + 90
    application.setDelegate_(delegate)
    status = AppKit.NSStatusBar.systemStatusBar().statusItemWithLength_(AppKit.NSVariableStatusItemLength)
    status.button().setTitle_('WX')
    menu = AppKit.NSMenu.alloc().init()
    for title, action in [('Open WXCOMMAND-PRO', 'openDashboard:'), ('Quit WXCOMMAND-PRO', 'quit:')]:
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, '')
        item.setTarget_(delegate)
        menu.addItem_(item)
    status.setMenu_(menu)
    worker.start()
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        .2, delegate, 'checkStartup:', None, True)
    try:
        application.run()
    finally:
        timer.invalidate()
        server.should_exit = True
        worker.join(15)
        sock.close()


def main() -> None:
    # Windowed bundles have no terminal streams. Keep startup failures inspectable.
    log_dir = Path(os.environ.get('WXCOMMAND_LOG_DIR', str(Path.home() / 'Library/Logs/WXCOMMAND-PRO')))
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'desktop.log').open('a', buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            if '--self-test' in sys.argv:
                self_test()
            else:
                run_desktop()
        except BaseException:
            logging.exception('Desktop startup failed')
            if '--self-test' not in sys.argv:
                import AppKit
                alert = AppKit.NSAlert.alloc().init()
                alert.setMessageText_('WXCOMMAND-PRO could not start')
                alert.setInformativeText_('Another instance may already be running. See ' + str(log_dir / 'desktop.log'))
                alert.runModal()
            raise
