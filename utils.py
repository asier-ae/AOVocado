# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Small standalone helpers shared across AOVocado's UI modules.
"""

import os
import re
from functools import wraps

import nuke

from ._vendor.Qt.QtCore import QSize
from ._vendor.Qt.QtGui import QColor, QCursor, QIcon, QPainter, QPixmap
from ._vendor.Qt.QtWidgets import QApplication

# Shared square icon size (pixels) for every icon-only button - all of
# them are 30x30 in the .ui files. A single default here, rather than each
# call site picking its own number, is what keeps every icon the same
# visual size; the icons themselves also all have consistent padding
# baked in for the same reason (see icons/ generation notes).
STANDARD_ICON_SIZE = 30

# 85% white - every icon in this app is tinted to this via load_icon()
# rather than baked into the PNG files, so the source assets stay pure
# white/full quality and this stays one tunable value.
STANDARD_ICON_TINT = QColor(217, 217, 217)


def load_icon(icon_path, tint=STANDARD_ICON_TINT):
    """Loads an icon file and recolors it to `tint`, preserving its alpha shape.

    Draws the icon, then fills everywhere it drew something with `tint`
    (`QPainter.CompositionMode_SourceIn` only paints inside existing
    alpha) - so the icon's silhouette/antialiasing is unchanged, just its
    color.

    Args:
        icon_path (str): Path to the icon image (expected: solid white on
            transparent, like everything in `icons/`).
        tint (QColor, optional): Color to recolor the icon to. Defaults to
            `STANDARD_ICON_TINT`.

    Returns:
        QIcon: The tinted icon.
    """
    source = QPixmap(icon_path)
    tinted = QPixmap(source.size())
    tinted.fill(QColor(0, 0, 0, 0))

    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), tint)
    painter.end()

    return QIcon(tinted)


# Nuke writes each top-level node in a .nk file as an unindented
# "SomeClass {" block; nested/internal nodes (e.g. inside a Group) are
# indented. Matching only unindented lines counts top-level nodes without
# needing to actually paste the file into the live script.
_TOP_LEVEL_NODE_PATTERN = re.compile(r"^[A-Za-z_]\w*\s*\{")


def _move_to_cursor(main_window):
    """Positions a window centered on the current mouse cursor location.

    Args:
        main_window (QWidget): The window to move. Its current size() is
            used to compute the centering offset (integer division is
            intentional - sub-pixel window positions aren't meaningful).
    """
    cursor_pos = QCursor().pos()
    window_size = main_window.size()
    main_window.move(
        cursor_pos.x() - window_size.width() // 2,
        cursor_pos.y() - window_size.height() // 2,
    )


def deselect_all_nodes():
    """Deselects every node in the current Nuke script.

    Used before/between node-graph creation steps to stop Nuke's default
    `createNode()` auto-connect behavior from chaining a new node onto
    whatever happens to still be selected from a previous step.
    """
    for node in nuke.selectedNodes():
        node["selected"].setValue(False)


def undo_block(func):
    """Decorator that wraps a function's node-graph edits in one Nuke undo step.

    Lets the whole decorated call be undone with a single Ctrl+Z instead of
    once per individual node operation. Uses try/finally so `nuke.Undo.end()`
    always runs, even if `func` raises - an unclosed undo block would leave
    Nuke's undo stack stuck merging every subsequent action into this one
    until Nuke is restarted.

    Args:
        func (Callable): The function to wrap.

    Returns:
        Callable: The wrapped function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        nuke.Undo.begin("AOVocado function undo")
        try:
            return func(*args, **kwargs)
        finally:
            nuke.Undo.end()

    return wrapper


def find_window_by_title(title):
    """Finds a top-level Qt widget by its window title.

    Args:
        title (str): The window title to search for.

    Returns:
        QWidget or None: The matching top-level widget, if any.
    """
    for widget in QApplication.topLevelWidgets():
        if widget.windowTitle() == title:
            return widget
    return None


def copy_to_clipboard(text):
    """Copies text to the system clipboard.

    Uses Qt's own QClipboard rather than shelling out to a platform tool
    QApplication.clipboard() works the same way on Windows, macOS,
    and Linux, since it's Qt's own cross-platform abstraction over each
    platform's native clipboard.

    Args:
        text (str): The text to place on the clipboard.
    """
    QApplication.clipboard().setText(text)


def set_button_icon(button, icon_path, size=STANDARD_ICON_SIZE, tooltip=None):
    """Configures a button's static icon, clearing its placeholder text.

    Shared by every icon-only button's one-time setup (settings, copy,
    subtractive rebuild, live sampler). Defaults to `STANDARD_ICON_SIZE` -
    without an explicit `size`, Qt falls back to its own default button
    icon size (commonly ~16px), which looks tiny and inconsistent next to
    every other icon button in this panel.

    Args:
        button (QPushButton): The button to configure.
        icon_path (str): Path to the icon image.
        size (int, optional): Square icon size in pixels. Defaults to
            `STANDARD_ICON_SIZE`; override only for a button that's
            deliberately a different size than the rest.
        tooltip (str, optional): Tooltip text. Omit to leave the button's
            existing tooltip (e.g. one already set in the `.ui` file).
    """
    button.setText("")
    button.setIcon(load_icon(icon_path))
    button.setIconSize(QSize(size, size))
    if tooltip is not None:
        button.setToolTip(tooltip)


def validate_toolset_path(path):
    """Checks whether `path` is a usable single-node toolset/group file.

    A toolset must resolve to exactly one top-level node when loaded
    (via `nuke.loadToolset()`), since that's the one node a channel's knob
    gets set on - same constraint a single Gizmo/Group already satisfies
    when creating nodes by class. Checked by scanning the file as text
    rather than loading it into the live script - see `node_creation.py`.

    Args:
        path (str): Path to the .nk file to check.

    Returns:
        str or None: None if `path` is a usable single-node toolset,
            otherwise a short human-readable reason it isn't.
    """
    if not path:
        return "No path given."
    if not os.path.isfile(path):
        return f"File not found: {path}"

    with open(path, "r", encoding="utf-8") as f:
        top_level_count = sum(1 for line in f if _TOP_LEVEL_NODE_PATTERN.match(line))

    if top_level_count == 0:
        return f"No nodes found in: {path}"
    if top_level_count > 1:
        return f"Contains {top_level_count} nodes (expected exactly 1): {path}"
    return None


def update_mode_button_visuals(
    button, icon_h_path, icon_v_path, size=STANDARD_ICON_SIZE
):
    """Sets a checkable mode button's icon/tooltip to match its checked state.

    Shared between `AOVocado.py`'s per-button mode toggles (b1_mode..b4_mode)
    and `settings_window.py`'s equivalents (BUTTON1_ICONMODE..BUTTON4_ICONMODE)
    - both use the same checked-means-horizontal convention.

    Args:
        button (QPushButton): The checkable button to update. Checked means
            horizontal node creation, unchecked means vertical.
        icon_h_path (str): Path to the horizontal-mode icon.
        icon_v_path (str): Path to the vertical-mode icon.
        size (int, optional): Square icon size in pixels. Defaults to
            `STANDARD_ICON_SIZE`, matching every other icon button.
    """
    button.setIconSize(QSize(size, size))
    if button.isChecked():
        button.setIcon(load_icon(icon_h_path))
        button.setToolTip("Creating nodes in a horizontal stack")
    else:
        button.setIcon(load_icon(icon_v_path))
        button.setToolTip("Creating nodes in a vertical stack")
