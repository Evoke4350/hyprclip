import sqlite3
from pathlib import Path

import pytest

from hyprclip.core import ClipStore, format_menu_line, parse_menu_selection, truncate_middle


def test_store_add_deduplicates_and_moves_existing_clip_to_top(tmp_path):
    db = tmp_path / "clips.sqlite3"
    store = ClipStore(db)

    first = store.add("hello world", mime="text/plain")
    second = store.add("another", mime="text/plain")
    again = store.add("hello world", mime="text/plain")

    assert first == again
    clips = store.list(limit=10)
    assert [clip.text for clip in clips] == ["hello world", "another"]
    assert clips[0].id == first
    assert clips[0].last_used_at >= clips[1].last_used_at


def test_store_ignores_empty_and_limits_history(tmp_path):
    store = ClipStore(tmp_path / "clips.sqlite3", max_items=3)

    assert store.add("   \n\t  ") is None
    for i in range(5):
        store.add(f"clip {i}")

    assert [clip.text for clip in store.list(limit=10)] == ["clip 4", "clip 3", "clip 2"]


def test_store_searches_case_insensitively(tmp_path):
    store = ClipStore(tmp_path / "clips.sqlite3")
    store.add("Deploy to production")
    store.add("open https://example.com")
    store.add("local note")

    assert [clip.text for clip in store.list(query="PROD")] == ["Deploy to production"]
    assert [clip.text for clip in store.list(query="https")] == ["open https://example.com"]


def test_format_and_parse_menu_line_handles_multiline_text():
    store_line = format_menu_line(42, "first line\nsecond line", max_preview=80)

    assert store_line.startswith("42\tfirst line ⏎ second line")
    assert parse_menu_selection(store_line) == 42


def test_truncate_middle_keeps_front_and_back():
    text = "abcdefghijklmnopqrstuvwxyz"

    assert truncate_middle(text, 11) == "abcde…vwxyz"


def test_parse_menu_selection_rejects_invalid_values():
    with pytest.raises(ValueError):
        parse_menu_selection("not-an-id no tab")
