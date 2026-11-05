"""Offline priority queue regression tests; never transmit RF."""
from collections import deque
import asyncio

from app.alert_priority import is_urgent_weather
from app.transmit import TransmitManager


class Db:
    def __init__(self):
        self.events = []

    def add_event(self, *args):
        self.events.append(args)


def make_manager(limit=10):
    m = TransmitManager.__new__(TransmitManager)
    m._db = Db()
    m._queue = deque(maxlen=limit)
    m._queue_low = deque(maxlen=limit)
    m._queue_event = asyncio.Event()
    return m


def test_only_known_urgent_warning_events_are_promoted():
    assert is_urgent_weather("NWS: Tornado Warning for county")
    assert is_urgent_weather("FLASH-FLOOD WARNING")
    assert not is_urgent_weather("Tornado Watch")
    assert not is_urgent_weather("Severe Thunderstorm Warning")
    assert not is_urgent_weather("notatornado warning")


def test_urgent_warning_jumps_ahead_of_routine_messages():
    m = make_manager()
    m.enqueue("routine weather update")
    m.enqueue("TORNADO WARNING for county")
    m.enqueue("another routine update")
    assert [item.text for item in m._queue] == [
        "TORNADO WARNING for county", "routine weather update", "another routine update"
    ]


def test_urgent_messages_keep_fifo_order():
    m = make_manager()
    m.enqueue("routine")
    m.enqueue("TORNADO WARNING A")
    m.enqueue("FLASH FLOOD WARNING B")
    assert [item.text for item in m._queue] == [
        "TORNADO WARNING A", "FLASH FLOOD WARNING B", "routine"
    ]


def test_priority_insert_when_full_reports_oldest_drop():
    m = make_manager(limit=2)
    failures = []
    m.enqueue("oldest", on_result=lambda ok, err: failures.append((ok, err)))
    m.enqueue("routine")
    assert not m.enqueue("TORNADO WARNING")
    assert failures == [(False, "dropped (queue full)")]
    assert [item.text for item in m._queue] == ["TORNADO WARNING", "routine"]


def test_ipaws_lane_is_not_reordered():
    m = make_manager()
    m.enqueue_ipaws("routine")
    m.enqueue_ipaws("TORNADO WARNING")
    assert [item.text for item in m._queue_low] == ["routine", "TORNADO WARNING"]
