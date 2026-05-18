# hyprclip

A tiny MIT-licensed clipboard manager built for Hyprland/Omarchy.

`hyprclip` watches your Wayland clipboard, keeps a searchable text history in SQLite, and opens that history from a Hyprland keybind with `walker` by default. It also falls back to `rofi`, `wofi`, `fuzzel`, or `gum` if you use another launcher.

## Features

- Wayland-native clipboard access via `wl-copy`/`wl-paste`.
- Searchable clipboard history stored locally in SQLite.
- `walker --dmenu` integration for Omarchy/Hyprland.
- Launcher fallbacks: `rofi`, `wofi`, `fuzzel`, `gum`.
- Deduplicates clips and moves reused clips to the top.
- Simple Hyprland install command for autostart + `SUPER+V` binding.

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
bindd = SUPER, V, Clipboard history, exec, hyprclip pick
```

Reload Hyprland after installing:

```bash
hyprctl reload
hyprctl dispatch exec 'uwsm-app -- hyprclip daemon'
```

Press `SUPER+V` to open clipboard history.

## Commands

```bash
hyprclip daemon              # watch clipboard continuously
hyprclip pick                # open picker and copy chosen item
hyprclip list -n 20          # print history
hyprclip add "manual text"   # add text manually
hyprclip clear               # clear saved history
hyprclip install             # install wrapper + Hyprland config lines
```

The clipboard database lives at:

```text
~/.local/share/hyprclip/clips.sqlite3
```

## Development

```bash
cd hyprclip
pytest -q
PYTHONPATH=src python -m hyprclip.cli --help
```

## License

MIT © Nate Bennett
