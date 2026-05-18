# hyprclip

A tiny MIT-licensed clipboard manager built for Hyprland/Omarchy.

`hyprclip` watches your Wayland clipboard, keeps a searchable text history in SQLite, and opens that history from a Hyprland keybind with `walker` by default. It also falls back to `rofi`, `wofi`, `fuzzel`, or `gum` if you use another launcher.

## Features

- Wayland-native clipboard access via `wl-copy`/`wl-paste`.
- Searchable clipboard history stored locally in SQLite.
- `walker --dmenu` integration for Omarchy/Hyprland.
- Polished picker rows with icons for URLs, commands/code, multiline clips, and text.
- Waybar custom module JSON for a top-right Omarchy clipboard indicator.
- Launcher fallbacks: `rofi`, `wofi`, `fuzzel`, `gum`.
- Deduplicates clips and moves reused clips to the top.
- Simple Hyprland install command for autostart + esoteric `SUPER+ALT+SHIFT+V` binding.

## Requirements

- Linux Wayland session, tested on Hyprland/Omarchy.
- Python 3.10+.
- [`wl-clipboard`](https://github.com/bugaevc/wl-clipboard): `wl-copy` and `wl-paste`.
- One picker: `walker`, `rofi`, `wofi`, `fuzzel`, or `gum`.
- Optional: `notify-send` for desktop notifications.

## Install from source

```bash
git clone https://github.com/Evoke4350/hyprclip.git
cd hyprclip
python -m pytest -q
PYTHONPATH=src python -m hyprclip.cli install
```

`hyprclip install` creates `~/.local/bin/hyprclip` and adds:

```conf
# ~/.config/hypr/autostart.conf
exec-once = uwsm-app -- hyprclip daemon

# ~/.config/hypr/bindings.conf
bindd = SUPER ALT SHIFT, V, Clipboard history, exec, hyprclip pick
```

Reload Hyprland after installing:

```bash
hyprctl reload
hyprctl dispatch exec 'uwsm-app -- hyprclip daemon'
```

Press `SUPER+ALT+SHIFT+V` to open clipboard history. `SUPER+V` is left alone so it can keep behaving like paste/app-native clipboard history.

## Commands

```bash
hyprclip daemon              # watch clipboard continuously
hyprclip pick                # open picker and copy chosen item
hyprclip list -n 20          # print history
hyprclip status              # print compact status, e.g. 󰅇 24
hyprclip waybar              # print Waybar custom module JSON
hyprclip install-waybar      # add top-right Waybar indicator to Omarchy config
hyprclip add "manual text"   # add text manually
hyprclip clear               # clear saved history
hyprclip install             # install wrapper + Hyprland config lines
```

The clipboard database lives at:

```text
~/.local/share/hyprclip/clips.sqlite3
```

## Waybar / Omarchy indicator

Run:

```bash
hyprclip install-waybar
pkill waybar && uwsm-app -- waybar
```

This adds a `custom/hyprclip` module to `~/.config/waybar/config.jsonc`:

```json
"custom/hyprclip": {
  "exec": "hyprclip waybar",
  "return-type": "json",
  "interval": 2,
  "on-click": "hyprclip pick",
  "on-click-right": "hyprclip clear",
  "tooltip": true
}
```

The module shows a clipboard icon plus clip count. Click it to open history; right-click clears history.

## Development

```bash
cd hyprclip
pytest -q
PYTHONPATH=src python -m hyprclip.cli --help
```

## License

MIT © Nate Bennett
