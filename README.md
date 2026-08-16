<p align="center">
  <img width="256" height="256" alt="avocado" src="https://github.com/user-attachments/assets/a95ba29f-bf46-4838-86f5-87af63dcdd82" />
</p>

# AOVocado

A Nuke panel for browsing, categorizing, and viewing render channels/AOVs
in the Viewer.

<img width="648" height="732" alt="Screenshot 2026-08-16 at 1 35 53 pm" src="https://github.com/user-attachments/assets/9ac65a98-00aa-4866-97f8-409c9c4c5ec6" />

## Features

- Channels from the viewer's input are automatically split into 4
  configurable groups, with a live search filter across all of them.
- Click a channel to view it in the Viewer; Ctrl/Shift-click and Ctrl+A for
  multi-select.
- Four configurable node-creation buttons — pick the node class/knob per
  button, and toggle vertical/horizontal layout.
- Live pixel sampler — hold the sampler button and Ctrl+click/drag in the
  Viewer to filter the lists down to just the channels active at that pixel.
- Subtractive rebuild — isolate a channel out of a beauty pass into its own
  output layer, wrapped in a styled backdrop.
- Copy selected channel names to the clipboard.
- Panel reloads automatically when the Viewer's connected input changes.

## Requirements

- Nuke 16 or newer.

## Installation

Copy the inner `AOVocado/` folder (the one containing `__init__.py`) into a
location on your Nuke plugin path (e.g. `~/.nuke/`), then add to
your `menu.py`:

```python
import AOVocado
```

That's it — on import, AOVocado registers itself under
**Edit > AOVocado > Open AOVocado**, with a hotkey (default `` Ctrl+` ``).

If you're developing directly out of a cloned copy of this repo instead of
copying the inner folder out, add the repo root itself to the plugin path
before importing, since it now sits one level above the actual package:

```python
nuke.pluginAddPath("/path/to/cloned/AOVocado")
import AOVocado
```

## Usage

Connect a Viewer to a node with multiple channels, then open the panel via
the hotkey or the menu entry. The same hotkey closes it again.

## Configuration

Open the Settings window (avocado icon in the panel) to configure the
node-creation buttons, node spacing, the live sampler's threshold, and the
subtractive rebuild's layout. Channel grouping rules and the hotkey are set
in `AOVocado_global_settings.json`.

## Debug logging

Debug logging is silent by default. To enable it, set the
`AOVOCADO_DEBUG` environment variable to any non-empty value *before*
launching Nuke:

```bash
export AOVOCADO_DEBUG=1
nuke
```

With it enabled, DEBUG-level trace for panel lifecycle, settings, channel
population, node/rebuild creation, viewer reloads, and the live sampler is
printed to the terminal/Script Editor, and also written to
`~/.nuke/AOVocado_debug.log` (useful if Nuke was launched from somewhere
without a visible terminal, e.g. a pipeline tool or desktop shortcut).

## Author

Asier Aparicio

## License

MIT — see [LICENSE](LICENSE).

## Third-party software

This project includes Qt.py, which is licensed under the MIT License.
See [`_vendor/Qt.py`](_vendor/Qt.py) for its original copyright and license
information.
