"""Tests for src/discovery.py (no Sonos hardware needed)."""

from types import SimpleNamespace

from src.discovery import discover_speakers, find_coordinator


def test_no_speakers_returns_empty_list():
    # soco.discover() returns None when nothing answers
    assert discover_speakers(lambda: None) == []
    assert discover_speakers(lambda: set()) == []


def test_no_speakers_coordinator_is_none():
    assert find_coordinator(lambda: None) is None


def test_coordinator_of_first_speaker():
    coord = SimpleNamespace(ip_address="10.0.0.2")
    spk = SimpleNamespace(group=SimpleNamespace(coordinator=coord))
    assert find_coordinator(lambda: [spk]) is coord
