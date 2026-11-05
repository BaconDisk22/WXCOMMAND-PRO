"""IPAWS CAP reference and demo filtering regression tests.

These tests never connect to a radio or fetch live alerts.
"""
from app.ipaws import _ref_identifiers, _is_demo, _ascii


def test_cap_update_references_extract_identifiers():
    refs = "agency@example.org,first-id,2026-10-13T12:00:00Z agency@example.org,second-id,2026-10-13T12:05:00Z"
    assert _ref_identifiers(refs) == ["first-id", "second-id"]


def test_cap_references_empty_and_invalid_entries():
    assert _ref_identifiers(None) == []
    assert _ref_identifiers("") == []
    assert _ref_identifiers("invalid") == []


def test_ipaws_demo_detection_does_not_flag_real_tornado_warning():
    assert not _is_demo({"event": "Tornado Warning", "identifier": "real-123"})


def test_ascii_mesh_payload_removes_controls():
    assert _ascii("  Tornado\nWarning\tnear\u00a0town  ") == "Tornado Warning near town"
