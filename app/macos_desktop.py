"""Native window, menus and server lifecycle for the standalone Mac build."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import socket
import sys
import threading
import time
from urllib.parse import urlsplit


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
                   'AppKit', 'Foundation', 'WebKit', 'certifi'):
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


def is_app_url(url: str, origin: str) -> bool:
    """Only the local server's pages stay in the app window; the rest go to the browser."""
    if url in ('', 'about:blank'):
        return True
    parsed, own = urlsplit(url), urlsplit(origin)
    return (parsed.scheme, parsed.netloc) == (own.scheme, own.netloc)


def run_desktop() -> None:
    import AppKit
    from Foundation import NSURL, NSURLRequest, NSMakeRect, NSObject, NSTimer
    import objc
    import WebKit
    import uvicorn
    from app.config import load_bootstrap
    from app.main import app

    cfg = load_bootstrap()
    sock = reserve_socket(cfg.http_host, cfg.http_port)
    browse_host = '127.0.0.1' if cfg.http_host in ('0.0.0.0', '::') else cfg.http_host
    if ':' in browse_host:
        browse_host = f'[{browse_host}]'
    origin = f'http://{browse_host}:{cfg.http_port}'
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, loop='asyncio'))
    worker = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    application = AppKit.NSApplication.sharedApplication()
    application.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)

    def open_external(nsurl):
        AppKit.NSWorkspace.sharedWorkspace().openURL_(nsurl)

    def run_alert(text, buttons):
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_(text)
        for title in buttons:
            alert.addButtonWithTitle_(title)
        return alert.runModal() == AppKit.NSAlertFirstButtonReturn

    # PyObjC cannot call WebKit's completion blocks without their signatures;
    # an uncalled decision handler leaves the window permanently blank. Declaring
    # the WebKit protocols on the class would override these, so it declares none.
    for selector, index, argument in (
            (b'webView:decidePolicyForNavigationAction:decisionHandler:', 4, b'q'),
            (b'webView:runJavaScriptAlertPanelWithMessage:initiatedByFrame:completionHandler:', 5, None),
            (b'webView:runJavaScriptConfirmPanelWithMessage:initiatedByFrame:completionHandler:', 5, b'Z')):
        arguments = {0: {'type': b'^v'}}
        if argument:
            arguments[1] = {'type': argument}
        objc.registerMetaDataForSelector(b'NSObject', selector, {'arguments': {
            index: {'type': b'@?', 'callable': {'retval': {'type': b'v'}, 'arguments': arguments}}}})

    class DesktopDelegate(NSObject):
        def showPath_(self, path):
            self.window.makeKeyAndOrderFront_(None)
            application.activateIgnoringOtherApps_(True)
            if server.started:
                request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(origin + path))
                self.webview.loadRequest_(request)

        def showOperator_(self, sender):
            self.showPath_('/operator')

        def showDashboard_(self, sender):
            self.showPath_('/')

        def showSettings_(self, sender):
            self.showPath_('/settings')

        def reload_(self, sender):
            self.webview.reload()

        def goBack_(self, sender):
            self.webview.goBack()

        def goForward_(self, sender):
            self.webview.goForward()

        # Closing the window keeps the server (and alert broadcasting) running.
        def windowShouldClose_(self, sender):
            sender.orderOut_(None)
            return False

        def applicationShouldHandleReopen_hasVisibleWindows_(self, sender, visible):
            self.window.makeKeyAndOrderFront_(None)
            return True

        def applicationShouldTerminate_(self, sender):
            server.should_exit = True
            worker.join(15)
            return AppKit.NSTerminateNow

        def webView_decidePolicyForNavigationAction_decisionHandler_(self, webview, action, handler):
            target = action.request().URL()
            frame = action.targetFrame()
            if (frame is None or frame.isMainFrame()) and not is_app_url(str(target.absoluteString()), origin):
                open_external(target)
                handler(WebKit.WKNavigationActionPolicyCancel)
            else:
                handler(WebKit.WKNavigationActionPolicyAllow)

        def webView_didFailProvisionalNavigation_withError_(self, webview, navigation, error):
            if error.code() != -999:  # NSURLErrorCancelled: the startup page being replaced
                logging.warning('Operator window failed to load: %s', error)

        def webView_didFailNavigation_withError_(self, webview, navigation, error):
            logging.warning('Operator window navigation failed: %s', error)

        def webView_didFinishNavigation_(self, webview, navigation):
            logging.info('Operator window loaded %s', webview.URL())

        # A crashed WebKit content process leaves a blank window; recover it.
        def webViewWebContentProcessDidTerminate_(self, webview):
            logging.warning('Operator window content process ended; reloading')
            self.showOperator_(None)

        # target="_blank" links: our pages open in this window, others in the browser.
        def webView_createWebViewWithConfiguration_forNavigationAction_windowFeatures_(
                self, webview, configuration, action, features):
            target = action.request().URL()
            if is_app_url(str(target.absoluteString()), origin):
                webview.loadRequest_(action.request())
            else:
                open_external(target)
            return None

        def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
                self, webview, message, frame, handler):
            run_alert(message, ['OK'])
            handler()

        # Manual send asks "Transmit this message now?"; without this it silently cancels.
        def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
                self, webview, message, frame, handler):
            handler(run_alert(message, ['OK', 'Cancel']))

        def checkStartup_(self, timer):
            if server.started:
                timer.invalidate()
                self.showOperator_(None)
            elif not worker.is_alive() or time.monotonic() > self.deadline:
                timer.invalidate()
                alert = AppKit.NSAlert.alloc().init()
                alert.setMessageText_('WXCOMMAND-PRO could not start')
                alert.setInformativeText_('See ~/Library/Logs/WXCOMMAND-PRO/desktop.log for details.')
                alert.runModal()
                application.terminate_(None)

    delegate = DesktopDelegate.alloc().init()
    delegate.deadline = time.monotonic() + 90

    style = (AppKit.NSWindowStyleMaskTitled | AppKit.NSWindowStyleMaskClosable
             | AppKit.NSWindowStyleMaskMiniaturizable | AppKit.NSWindowStyleMaskResizable)
    window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, 1280, 860), style, AppKit.NSBackingStoreBuffered, False)
    window.setTitle_('WXCOMMAND-PRO Operator Center')
    window.setMinSize_(AppKit.NSMakeSize(720, 520))
    window.center()
    window.setFrameAutosaveName_('WXCOMMAND-PRO Operator Center')
    window.setReleasedWhenClosed_(False)
    window.setDelegate_(delegate)
    webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
        window.contentView().bounds(), WebKit.WKWebViewConfiguration.alloc().init())
    webview.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
    webview.setNavigationDelegate_(delegate)
    webview.setUIDelegate_(delegate)
    webview.loadHTMLString_baseURL_(
        '<body style="background:#101a22;color:#9fb3c8;font:15px -apple-system;'
        'display:grid;place-items:center;height:90vh">Starting WXCOMMAND-PRO&hellip;</body>', None)
    window.contentView().addSubview_(webview)
    delegate.window, delegate.webview = window, webview

    def add_menu(title, items):
        top = AppKit.NSMenuItem.alloc().init()
        menu = AppKit.NSMenu.alloc().initWithTitle_(title)
        for entry in items:
            if entry is None:
                menu.addItem_(AppKit.NSMenuItem.separatorItem())
                continue
            label, action, key, own = entry
            item = menu.addItemWithTitle_action_keyEquivalent_(label, action, key)
            if own:
                item.setTarget_(delegate)
        top.setSubmenu_(menu)
        main_menu.addItem_(top)
        return menu

    # Standard menus; Edit is required for copy/paste in the web view's text fields.
    main_menu = AppKit.NSMenu.alloc().init()
    add_menu('WXCOMMAND-PRO', [('About WXCOMMAND-PRO', 'orderFrontStandardAboutPanel:', '', False), None,
                               ('Hide WXCOMMAND-PRO', 'hide:', 'h', False), None,
                               ('Quit WXCOMMAND-PRO', 'terminate:', 'q', False)])
    add_menu('Edit', [('Undo', 'undo:', 'z', False), ('Redo', 'redo:', 'Z', False), None,
                      ('Cut', 'cut:', 'x', False), ('Copy', 'copy:', 'c', False),
                      ('Paste', 'paste:', 'v', False), ('Select All', 'selectAll:', 'a', False)])
    add_menu('View', [('Operator Center', 'showOperator:', '1', True),
                      ('Dashboard', 'showDashboard:', '2', True),
                      ('Settings', 'showSettings:', ',', True), None,
                      ('Back', 'goBack:', '[', True), ('Forward', 'goForward:', ']', True),
                      ('Reload', 'reload:', 'r', True)])
    window_menu = add_menu('Window', [('Minimize', 'performMiniaturize:', 'm', False),
                                      ('Close', 'performClose:', 'w', False), None,
                                      ('Operator Center', 'showOperator:', '0', True)])
    application.setMainMenu_(main_menu)
    application.setWindowsMenu_(window_menu)
    application.setDelegate_(delegate)

    window.makeKeyAndOrderFront_(None)
    application.activateIgnoringOtherApps_(True)
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
