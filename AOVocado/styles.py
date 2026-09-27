# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Centralized QSS styling for both AOVocado windows.

Replaces per-widget `pointsize`/`bold` properties scattered across the two
`.ui` files with one stylesheet built by `build_stylesheet()` and applied
via `setStyleSheet()`, plus a small `class` dynamic property on the few
widgets that need to deviate from the base look (section headers,
sub-headers, the one note, the one muted label). No font-family or
font-size is set anywhere in the stylesheet itself, deliberately - every
widget keeps inheriting Nuke's own default Qt font for the current OS
(confirmed via testing on both macOS and Linux/PCoIP: this alone matches
Nuke's own UI correctly, no computation needed), so text stays visually
consistent with the rest of Nuke's interface. The header/note/muted
classes still need to be relatively bigger/smaller than that inherited
base - handled by `apply_relative_font_sizes()` below, not QSS, since a
QSS `font-size` rule doesn't reliably resolve onto a widget's effective
font in this Qt/PySide/Nuke combination (confirmed: a `px`-based rule
sits in a widget's `styleSheet()` text but never actually applies to its
font - `resolveMask()` stays 0), and a `pt`-based one would reintroduce
the DPI-dependent cross-platform mismatch this whole mechanism exists to
avoid (a hardcoded `12pt` base is what caused the original bug: Linux/PCoIP
remote sessions don't always report the same DPI as macOS, so the same
point size converts to a visibly different pixel size on each).
"""

from ._vendor.Qt.QtWidgets import QWidget


def build_stylesheet():
    """Builds the QSS stylesheet.

    Returns:
        str: The QSS stylesheet.
    """
    return """
QWidget {
}
QGroupBox {
    font-weight: bold;
}
QPushButton {
    min-height: 30px;
}
QSpinBox, QDoubleSpinBox {
    min-height: 30px;
}
QLineEdit, QComboBox {
    min-height: 30px;
}
/* Deliberately no QKeySequenceEdit rule here. It doesn't paint itself via
   QStyle subcontrols like QLineEdit/QComboBox do - it's a plain QWidget
   wrapping an internal child QLineEdit. Styling the outer QKeySequenceEdit
   directly (even just min-height) puts its own box model at odds with the
   inner one and clips the rendered text. The inner child already picks up
   the QLineEdit rule above on its own (it IS a QLineEdit), which is enough
   - leave the outer widget's height alone. */
QLabel[class="header"] {
    font-weight: bold;
}
QLabel[class="subheader"] {
    font-weight: bold;
}
QLabel[class="note"] {
    font-style: italic;
}
QLabel[class="muted"] {
    color: rgb(120, 120, 120);
}
"""


# Font-size deltas for each class tag, applied directly to each tagged
# widget's own QFont by apply_relative_font_sizes() below - not through
# QSS (see the module docstring for why). "subheader" is intentionally
# absent - it only gets bold weight, no size change.
_SIZE_OFFSETS = {
    "header": 1,
    "note": -1,
    "muted": 0,
}


def apply_relative_font_sizes(root_widget, widget_classes):
    """Nudges each tagged label's font size relative to its own current size.

    Deliberately not done via QSS `font-size` - see the module docstring.
    Reads each widget's own already-correctly-inherited QFont and adjusts
    it by a small delta in whichever unit (pt or px) that font is already
    using - no DPI query, no absolute value, so nothing here can diverge
    across platforms the way a hardcoded pt value did.

    Args:
        root_widget (QWidget): The window the tagged widgets live on
            (`self` from `AOVocado.py`/`settings_window.py`).
        widget_classes (dict[str, str]): `{object_name: class_tag}`, e.g.
            `MAIN_PANEL_CLASSES` or `SETTINGS_CLASSES`.
    """
    for object_name, class_tag in widget_classes.items():
        offset = _SIZE_OFFSETS.get(class_tag)
        if not offset:
            continue
        widget = getattr(root_widget, object_name, None)
        if not isinstance(widget, QWidget):
            continue
        font = widget.font()
        if font.pointSizeF() > 0:
            font.setPointSizeF(font.pointSizeF() + offset)
        else:
            font.setPixelSize(font.pixelSize() + offset)
        widget.setFont(font)


# Only the outliers need an entry here - everything else matches the
# QWidget/QGroupBox base rules above and needs no per-widget tagging at
# all. Both windows have their own widget named "label_2" (unrelated to
# each other), hence two separate dicts rather than one shared by name.
MAIN_PANEL_CLASSES = {
    "label_2": "muted",  # "Create" label above the AOV create button
}

SETTINGS_CLASSES = {
    "label_70": "header",  # "Keyboard Shortcut"
    "label_74": "header",  # "Live Sampling"
    "label_39": "header",  # "Node Creation Setup"
    "label_35": "header",  # "Node Creation Setup" (Rebuild Subtractive tab)
    "label_95": "header",  # "Layout"
    "label_96": "header",  # "Node Spacing"
    "label_7": "header",  # "Info"
    "label_8": "header",  # "Shortcuts"
    "lb_title_version": "header",
    "label_97": "subheader",  # "Horizontal Node Separation"
    "label_100": "subheader",  # "Vertical Node Separation"
    "label_104": "subheader",  # "Backdrop Margins"
    "label_2": "note",  # "(restart nuke for this to take effect)"
}


def apply_style_classes(root_widget, widget_classes):
    """Tags each exception widget with its QSS `class` property.

    Must run after `loadUi()` and after `setStyleSheet()`. Qt doesn't
    automatically re-evaluate class-selector QSS rules for a dynamic
    property set on an already-constructed widget, so each one needs an
    explicit unpolish/polish cycle to pick up the new rule.

    Args:
        root_widget (QWidget): The window the tagged widgets live on
            (`self` from `AOVocado.py`/`settings_window.py`).
        widget_classes (dict[str, str]): `{object_name: class_tag}`, e.g.
            `MAIN_PANEL_CLASSES` or `SETTINGS_CLASSES`.
    """
    for object_name, class_tag in widget_classes.items():
        widget = getattr(root_widget, object_name, None)
        if not isinstance(widget, QWidget):
            continue
        widget.setProperty("class", class_tag)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
