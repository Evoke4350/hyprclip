import sqlite3
from pathlib import Path

import pytest

from hyprclip.core import (
    Clip,
    ClipStore,
    detect_clip_kind,
    format_menu_line,
    format_waybar_status,
    human_age,
    parse_menu_selection,
    truncate_middle,
)
from hyprclip.waybar import add_hyprclip_waybar_module


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
    clip = Clip(id=42, text="first line\nsecond line", mime="text/plain", created_at=0, last_used_at=120)
    store_line = format_menu_line(clip, max_preview=80, now=180)

    assert store_line.startswith("42\t󰦨 1m multiline  first line ⏎ second line")
    assert parse_menu_selection(store_line) == 42


def test_detect_clip_kind_labels_common_clip_types():
    assert detect_clip_kind("https://example.com/docs") == ("url", "󰖟")
    assert detect_clip_kind("git status && pytest -q") == ("command", "")
    assert detect_clip_kind("def hello():\n    return 'world'") == ("code", "󰅩")
    assert detect_clip_kind("line one\nline two") == ("multiline", "󰦨")
    assert detect_clip_kind("plain note") == ("text", "󰅇")


def test_human_age_uses_compact_relative_time():
    assert human_age(last_used_at=100, now=104) == "now"
    assert human_age(last_used_at=100, now=160) == "1m"
    assert human_age(last_used_at=100, now=7_300) == "2h"
    assert human_age(last_used_at=100, now=180_000) == "2d"


def test_format_waybar_status_reports_count_and_tooltip(tmp_path):
    store = ClipStore(tmp_path / "clips.sqlite3")
    store.add("https://example.com")
    store.add("plain note")

    status = format_waybar_status(store, now=180)

    assert status["text"] == "󰅇 2"
    assert status["class"] == "active"
    assert status["alt"] == "hyprclip"
    assert "plain note" in status["tooltip"]


def test_add_hyprclip_waybar_module_inserts_right_side_module():
    config = {"modules-right": ["network", "cpu"], "network": {}}

    updated = add_hyprclip_waybar_module(config)

    assert updated["modules-right"] == ["network", "custom/hyprclip", "cpu"]
    assert updated["custom/hyprclip"] == {
        "exec": "hyprclip waybar",
        "return-type": "json",
        "interval": 2,
        "on-click": "hyprclip pick",
        "on-click-right": "hyprclip clear",
        "tooltip": True,
    }


def test_add_hyprclip_waybar_module_is_idempotent():
    config = {"modules-right": ["network", "custom/hyprclip", "cpu"], "custom/hyprclip": {}}

    updated = add_hyprclip_waybar_module(config)

    assert updated["modules-right"].count("custom/hyprclip") == 1


def test_truncate_middle_keeps_front_and_back():
    text = "abcdefghijklmnopqrstuvwxyz"

    assert truncate_middle(text, 11) == "abcde…vwxyz"


def test_parse_menu_selection_rejects_invalid_values():
    with pytest.raises(ValueError):
        parse_menu_selection("not-an-id no tab")
