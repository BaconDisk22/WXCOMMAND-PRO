"""A dead Meshtastic link must read as disconnected so the watchdog recovers it.

Reproduced on hardware: with the radio powered off the library's reader thread
exited, yet status stayed connected/healthy and the app never reconnected.
"""
import asyncio
import threading
from collections import deque

import pytest

from app import transmit
from app.transmit import MeshtasticTransmitter, TransmitManager


class FakeIface:
    def __init__(self, link_up=True, reader_alive=True):
        self.isConnected = threading.Event()
        if link_up:
            self.isConnected.set()
        self._stop = threading.Event()
        self._rxThread = threading.Thread(target=self._stop.wait, daemon=True)
        if reader_alive:
            self._rxThread.start()

    def finish(self):
        self._stop.set()
        if self._rxThread.is_alive():
            self._rxThread.join(2)


def transmitter(iface):
    tx = MeshtasticTransmitter("tcp", host="radio.local")
    tx._iface = iface
    return tx


def test_live_link_reads_connected():
    iface = FakeIface()
    try:
        assert transmitter(iface).connected
    finally:
        iface.finish()


def test_no_interface_reads_disconnected():
    assert not transmitter(None).connected


def test_cleared_link_flag_reads_disconnected():
    iface = FakeIface(link_up=False)
    try:
        assert not transmitter(iface).connected
    finally:
        iface.finish()


def test_exited_reader_reads_disconnected():
    iface = FakeIface()
    iface.finish()  # the library's reader exits when the socket dies
    assert not transmitter(iface).connected


class FakeDb:
    def __init__(self):
        self.events = []

    def add_event(self, *args):
        self.events.append(args)

    def add_error(self, *args):
        pass


class DeadRadio:
    connected = False


class FakeTransport:
    name = "meshtastic"
    label = "Meshtastic"
    enabled = True
    target = "meshtastic.local"
    error = ""

    def __init__(self):
        self.tx = DeadRadio()
        self.connected = True


async def test_watchdog_marks_lost_link_and_reconnects(monkeypatch):
    db, t = FakeDb(), FakeTransport()
    mgr = TransmitManager.__new__(TransmitManager)
    mgr._db, mgr._lock, mgr._stopped = db, asyncio.Lock(), False
    mgr._transports = {t.name: t}
    mgr._connection_history = deque(maxlen=100)
    mgr._retry_after = {}
    reconnects = []

    async def fake_reconnect(transport):
        reconnects.append(transport.name)
        return False

    async def one_tick(_seconds):
        if reconnects:
            mgr._stopped = True

    monkeypatch.setattr(mgr, "_reconnect", fake_reconnect)
    monkeypatch.setattr(transmit.asyncio, "sleep", one_tick)
    await asyncio.wait_for(mgr._connection_watchdog(), 5)

    assert t.connected is False and t.error == "link lost"
    assert reconnects == ["meshtastic"]
    assert any("link lost" in str(e) for e in db.events)
    assert mgr._connection_history[-1]["event"] == "lost"
