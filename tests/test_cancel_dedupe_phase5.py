"""Regression tests for repeated NWS cancellation messages."""
from app.dedupe import decide
from app.filters import FilterRules
from app.models import Alert


RULES = FilterRules(include_exact=["Tornado Warning"], include_suffix=[], exclude_exact=[])


def cancellation():
    return Alert(nws_id="cancel-2", event="Tornado Warning", headline="cancel",
                 area_desc="County", effective="", expires="",
                 message_type="Cancel", references=["warning-1"])


def test_cancellation_sent_for_previously_broadcast_warning():
    states = {"warning-1": {"disposition": "sent", "msg_hash": "old",
                             "headline": "warning", "expires": ""}}
    decision = decide(cancellation(), RULES, states.get)
    assert decision.transmit and decision.disposition == "cancelled"


def test_cancellation_not_repeated_after_confirmed_broadcast():
    states = {"warning-1": {"disposition": "sent"},
              "cancel-2": {"disposition": "cancelled"}}
    decision = decide(cancellation(), RULES, states.get)
    assert not decision.transmit and decision.disposition == "duplicate"


def test_cancellation_retried_if_not_confirmed_sent():
    states = {"warning-1": {"disposition": "sent"}}
    assert decide(cancellation(), RULES, states.get).transmit


def test_unknown_cancellation_not_broadcast():
    decision = decide(cancellation(), RULES, {}.get)
    assert not decision.transmit
