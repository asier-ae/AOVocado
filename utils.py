"""Small standalone helpers shared across channelHub's UI modules.

Author: Asier Aparicio
"""

from functools import wraps

import nuke

from ._vendor.Qt.QtCore import QSize
from ._vendor.Qt.QtGui import QCursor, QIcon
from ._vendor.Qt.QtWidgets import QApplication


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
        nuke.Undo.begin("channelHub function undo")
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


def set_button_icon(button, icon_path, size=None, tooltip=None):
    """Configures a button's static icon, clearing its placeholder text.

    Shared by every icon-only button's one-time setup (settings, copy,
    subtractive rebuild, live sampler) - without an explicit `size`, Qt
    falls back to its default button icon size (commonly ~16px), which
    looks tiny and off-center inside this panel's 30x30 buttons.

    Args:
        button (QPushButton): The button to configure.
        icon_path (str): Path to the icon image.
        size (int, optional): Square icon size in pixels. Omit to leave
            Qt's default button icon size in place.
        tooltip (str, optional): Tooltip text. Omit to leave the button's
            existing tooltip (e.g. one already set in the `.ui` file).
    """
    button.setText("")
    button.setIcon(QIcon(icon_path))
    if size is not None:
        button.setIconSize(QSize(size, size))
    if tooltip is not None:
        button.setToolTip(tooltip)


def update_mode_button_visuals(button, icon_h_path, icon_v_path):
    """Sets a checkable mode button's icon/tooltip to match its checked state.

    Shared between `channelHub.py`'s per-button mode toggles (b1_mode..b4_mode)
    and `settings_window.py`'s equivalents (BUTTON1_ICONMODE..BUTTON4_ICONMODE)
    - both use the same checked-means-horizontal convention.

    Args:
        button (QPushButton): The checkable button to update. Checked means
            horizontal node creation, unchecked means vertical.
        icon_h_path (str): Path to the horizontal-mode icon.
        icon_v_path (str): Path to the vertical-mode icon.
    """
    if button.isChecked():
        button.setIcon(QIcon(icon_h_path))
        button.setToolTip("Creating nodes in a horizontal stack")
    else:
        button.setIcon(QIcon(icon_v_path))
        button.setToolTip("Creating nodes in a vertical stack")
