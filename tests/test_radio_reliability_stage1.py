"""Offline radio reliability regression tests. No real transmissions."""
import pytest

from app.transmit import TransmitManager, TxUnsent


class FakeDb:
    def __init__(self, failover=True):
        self.failover = failover
        self.logs = []
        self.errors = []

    def get_setting(self, key, default=None):
        if key == "radio_failover_enabled":
            return self.failover
        return default

    def add_transmit_log(self, *args, **kwargs):
        self.logs.append((args, kwargs))

    def add_error(self, *args):
        self.errors.append(args)

    def add_event(self, *args):
        pass


class FakeRadio:
    def __init__(self, outcome=None):
        self.outcome = outcome
        self.calls = []

    async def send_text(self, text, channel):
        self.calls.append((text, channel))
        if self.outcome is not None:
            raise self.outcome

    @property
    def connected(self):
        return True


class FakeTransport:
    def __init__(self, name, radio, channel=0):
        self.name = name
        self.label = name
        self.tx = radio
        self.enabled = True
        self.connected = True
        self.channel = channel
        self.test_channel = 1
        self.error = ""


def manager(db, *transports):
    obj = TransmitManager.__new__(TransmitManager)
    import asyncio
    obj._db = db
    obj._lock = asyncio.Lock()
    obj._transports = {t.name: t for t in transports}
    return obj


@pytest.mark.asyncio
async def test_failover_stops_after_first_confirmed_send():
    db = FakeDb(failover=True)
    first, second = FakeRadio(), FakeRadio()
    tx = manager(db, FakeTransport("meshtastic", first), FakeTransport("meshcore", second))
    assert await tx._send_all("test message", manual=False)
    assert first.calls == [("test message", 0)]
    assert second.calls == []
    assert len(db.logs) == 1


@pytest.mark.asyncio
async def test_fanout_sends_to_both_when_failover_disabled():
    db = FakeDb(failover=False)
    first, second = FakeRadio(), FakeRadio()
    tx = manager(db, FakeTransport("meshtastic", first), FakeTransport("meshcore", second))
    assert await tx._send_all("test message", manual=False)
    assert len(first.calls) == len(second.calls) == 1
    assert len(db.logs) == 2


@pytest.mark.asyncio
async def test_unrecoverable_channel_error_does_not_retry():
    db = FakeDb()
    radio = FakeRadio(TxUnsent("no_channel", "channel missing"))
    tx = manager(db, FakeTransport("meshtastic", radio))
    ok, err = await tx._try_send(tx._transports["meshtastic"], "test", 0)
    assert not ok
    assert err == "channel missing"
    assert len(radio.calls) == 1
    assert db.errors


@pytest.mark.asyncio
async def test_failover_uses_second_radio_if_first_cannot_send():
    db = FakeDb(failover=True)
    first = FakeRadio(TxUnsent("too_large", "rejected"))
    second = FakeRadio()
    tx = manager(db, FakeTransport("meshtastic", first), FakeTransport("meshcore", second))
    assert await tx._send_all("test", manual=False)
    assert len(first.calls) == 1
    assert len(second.calls) == 1
    assert len(db.logs) == 2


@pytest.mark.asyncio
async def test_failover_tries_connected_backup_before_disconnected_primary():
    db = FakeDb(failover=True)
    primary, backup = FakeRadio(), FakeRadio()
    down = FakeTransport("meshtastic", primary)
    down.connected = False
    tx = manager(db, down, FakeTransport("meshcore", backup))
    assert await tx._send_all("test", manual=False)
    assert backup.calls == [("test", 0)]
    assert primary.calls == []
