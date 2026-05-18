from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .core import ClipStore, format_menu_line, format_waybar_status, parse_menu_selection
from .waybar import install_hyprclip_waybar_module

APP_NAME = "hyprclip"
DEFAULT_DB = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / APP_NAME / "clips.sqlite3"


def run(cmd: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, check=check)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def read_clipboard() -> tuple[str, str]:
    mime = "text/plain"
    if command_exists("wl-paste"):
        types = run(["wl-paste", "--list-types"], check=False).stdout.splitlines()
        text_types = [t for t in types if t.startswith("text/") or t in {"UTF8_STRING", "STRING"}]
        if text_types:
            mime = text_types[0]
        out = run(["wl-paste", "--no-newline", "--type", mime], check=False)
        return out.stdout, mime
    raise RuntimeError("wl-paste is required on Wayland/Hyprland")


def write_clipboard(text: str) -> None:
    if not command_exists("wl-copy"):
        raise RuntimeError("wl-copy is required on Wayland/Hyprland")
    run(["wl-copy"], input_text=text)


def notify(message: str) -> None:
    if command_exists("notify-send"):
        subprocess.Popen(["notify-send", APP_NAME, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_add(args: argparse.Namespace) -> int:
    store = ClipStore(args.db, max_items=args.max_items)
    if args.text is not None:
        text, mime = args.text, "text/plain"
    else:
        text, mime = read_clipboard()
    clip_id = store.add(text, mime=mime)
    if args.verbose and clip_id is not None:
        print(clip_id)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    store = ClipStore(args.db, max_items=args.max_items)
    for clip in store.list(limit=args.limit, query=args.query):
        print(format_menu_line(clip, max_preview=args.preview_width))
    return 0


def choose_with_launcher(lines: str, prompt: str) -> str:
    if command_exists("walker"):
        return run(["walker", "--dmenu", "--placeholder", prompt], input_text=lines).stdout.strip()
    if command_exists("rofi"):
        return run(["rofi", "-dmenu", "-i", "-p", prompt], input_text=lines).stdout.strip()
    if command_exists("wofi"):
        return run(["wofi", "--dmenu", "--prompt", prompt], input_text=lines).stdout.strip()
    if command_exists("fuzzel"):
        return run(["fuzzel", "--dmenu", "--prompt", f"{prompt}> "], input_text=lines).stdout.strip()
    if command_exists("gum"):
        return run(["gum", "filter", "--placeholder", prompt], input_text=lines).stdout.strip()
    raise RuntimeError("Need walker, rofi, wofi, fuzzel, or gum for interactive picking")


def cmd_pick(args: argparse.Namespace) -> int:
    store = ClipStore(args.db, max_items=args.max_items)
    clips = store.list(limit=args.limit, query=args.query)
    if not clips:
        notify("No clipboard history yet")
        return 1
    menu = "\n".join(format_menu_line(c, max_preview=args.preview_width) for c in clips) + "\n"
    selection = choose_with_launcher(menu, "Clipboard")
    if not selection:
        return 1
    clip_id = parse_menu_selection(selection)
    clip = store.get(clip_id)
    if clip is None:
        notify("Selected clip disappeared")
        return 1
    write_clipboard(clip.text)
    store.touch(clip.id)
    notify("Copied selection to clipboard")
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    store = ClipStore(args.db, max_items=args.max_items)
    last_digest: str | None = None
    notify("Clipboard watcher started") if args.notify_start else None
    while True:
        try:
            text, mime = read_clipboard()
            digest = store.digest(text) if text.strip() else None
            if digest and digest != last_digest:
                store.add(text, mime=mime)
                last_digest = digest
        except Exception as exc:
            if args.verbose:
                print(f"{APP_NAME}: {exc}", file=sys.stderr)
        time.sleep(args.interval)


def cmd_clear(args: argparse.Namespace) -> int:
    count = ClipStore(args.db, max_items=args.max_items).clear()
    print(f"cleared {count} clips")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = ClipStore(args.db, max_items=args.max_items)
    status = format_waybar_status(store, tooltip_limit=args.tooltip_limit)
    if args.json:
        print(json.dumps(status, ensure_ascii=False))
    else:
        print(status["text"])
    return 0


def cmd_waybar(args: argparse.Namespace) -> int:
    store = ClipStore(args.db, max_items=args.max_items)
    print(json.dumps(format_waybar_status(store, tooltip_limit=args.tooltip_limit), ensure_ascii=False))
    return 0


def cmd_install_waybar(args: argparse.Namespace) -> int:
    changed = install_hyprclip_waybar_module(args.config)
    print(f"{'updated' if changed else 'already configured'} {args.config}")
    print("Restart Waybar or run: pkill waybar && uwsm-app -- waybar")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    bin_dir = Path.home() / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "hyprclip"
    repo = Path(__file__).resolve().parents[2]
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        f"export PYTHONPATH={repo / 'src'}:${{PYTHONPATH:-}}\n"
        "exec python3 -m hyprclip.cli \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    autostart = Path.home() / ".config/hypr/autostart.conf"
    bindings = Path.home() / ".config/hypr/bindings.conf"
    autostart_line = "exec-once = uwsm-app -- hyprclip daemon"
    binding_line = "bindd = SUPER, V, Clipboard history, exec, hyprclip pick"
    for path, line in [(autostart, autostart_line), (bindings, binding_line)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        if line not in content:
            backup = path.with_suffix(path.suffix + ".hyprclip.bak")
            if path.exists() and not backup.exists():
                backup.write_text(content, encoding="utf-8")
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"\n# {APP_NAME}\n{line}\n"
            path.write_text(content, encoding="utf-8")
    print(f"installed {wrapper}")
    print("Hyprland binding: SUPER+V opens clipboard history")
    print("Reload Hyprland or run: hyprctl reload")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hyprland/Omarchy clipboard manager")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--max-items", type=int, default=250)
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Add current clipboard or supplied text to history")
    add.add_argument("text", nargs="?")
    add.add_argument("-v", "--verbose", action="store_true")
    add.set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="Print menu-formatted clipboard history")
    ls.add_argument("-n", "--limit", type=int, default=50)
    ls.add_argument("-q", "--query")
    ls.add_argument("--preview-width", type=int, default=120)
    ls.set_defaults(func=cmd_list)

    pick = sub.add_parser("pick", help="Pick an entry with walker/rofi/wofi/fuzzel/gum and copy it")
    pick.add_argument("-n", "--limit", type=int, default=50)
    pick.add_argument("-q", "--query")
    pick.add_argument("--preview-width", type=int, default=120)
    pick.set_defaults(func=cmd_pick)

    daemon = sub.add_parser("daemon", help="Poll wl-paste and maintain clipboard history")
    daemon.add_argument("--interval", type=float, default=0.6)
    daemon.add_argument("-v", "--verbose", action="store_true")
    daemon.add_argument("--notify-start", action="store_true")
    daemon.set_defaults(func=cmd_daemon)

    clear = sub.add_parser("clear", help="Clear saved history")
    clear.set_defaults(func=cmd_clear)

    status = sub.add_parser("status", help="Print clipboard history status for scripts")
    status.add_argument("--json", action="store_true", help="Print Waybar-compatible JSON")
    status.add_argument("--tooltip-limit", type=int, default=5)
    status.set_defaults(func=cmd_status)

    waybar = sub.add_parser("waybar", help="Print Waybar custom module JSON")
    waybar.add_argument("--tooltip-limit", type=int, default=5)
    waybar.set_defaults(func=cmd_waybar)

    install_waybar = sub.add_parser("install-waybar", help="Add hyprclip to ~/.config/waybar/config.jsonc")
    install_waybar.add_argument("--config", type=Path, default=Path.home() / ".config/waybar/config.jsonc")
    install_waybar.set_defaults(func=cmd_install_waybar)

    install = sub.add_parser("install", help="Install ~/.local/bin wrapper and Hyprland autostart/keybinding")
    install.set_defaults(func=cmd_install)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
