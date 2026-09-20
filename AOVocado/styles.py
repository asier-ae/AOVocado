# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Centralized QSS styling for both AOVocado windows.

Replaces per-widget `pointsize`/`bold` properties scattered across the two
`.ui` files with one stylesheet built by `build_stylesheet()` and applied
via `setStyleSheet()`, plus a small `class` dynamic property on the few
widgets that need to deviate from the base look (section headers,
sub-headers, the one note, the one muted label). No font-family is set
anywhere here, deliberately - every widget keeps inheriting Nuke's own
default Qt font for the current OS, so text stays visually consistent with
the rest of Nuke's interface rather than introducing a font that might not
even be installed on a given machine. The base font *size* is inherited
the same way (via `_reference_font_size()` below) rather than hardcoded -
see that function's docstring for why.
"""

from ._vendor.Qt.QtWidgets import QApplication, QWidget


def _reference_font_size():
    """Reads the size and unit of Nuke's current default application font.

    AOVocado runs inside Nuke's own already-running QApplication, so this
    reflects exactly what Nuke itself uses as its default UI text size on
    whatever platform/remote-session it's running on - matching it directly
    avoids needing to know in advance whether Nuke uses points or pixels,
    or whether that differs across platforms (this bit AOVocado before: a
    hardcoded `12pt` base rendered visibly larger over a Linux/PCoIP remote
    session than on macOS, since point sizes are converted to pixels using
    the screen's reported logical DPI, which remote-display protocols don't
    always propagate correctly).

    Returns:
        tuple[float, str]: (size, unit), unit is "pt" or "px".
    """
    font = QApplication.font()
    point_size = font.pointSizeF()
    if point_size > 0:
        return point_size, "pt"
    return float(font.pixelSize()), "px"


def build_stylesheet(multiplier=1.0):
    """Builds the QSS stylesheet, scaled by a multiplier over Nuke's own font size.

    Args:
        multiplier (float): Scale factor over Nuke's live default font size
            (`cfg_sp_font_size` in Settings). 1.0 - the default - renders
            at exactly Nuke's own size; this is what makes the panel match
            Nuke's UI out of the box without any per-platform guessing.

    Returns:
        str: The QSS stylesheet.
    """
    ref_size, ref_unit = _reference_font_size()
    # Rounded to 2 decimals - float multiplication otherwise produces noisy
    # values like 14.399999999999999, which QSS would parse fine but is
    # needlessly sloppy to hand a stylesheet.
    base = round(ref_size * multiplier, 2)
    header = round(base + 1, 2)
    note = round(base - 1, 2)
    muted = round(base - 2, 2)

    return f"""
QWidget {{
    font-size: {base}{ref_unit};
}}
QGroupBox {{
    font-weight: bold;
}}
QPushButton {{
    min-height: 30px;
}}
QSpinBox, QDoubleSpinBox {{
    min-height: 30px;
}}
QLineEdit, QComboBox {{
    min-height: 30px;
}}
/* Deliberately no QKeySequenceEdit rule here. It doesn't paint itself via
   QStyle subcontrols like QLineEdit/QComboBox do - it's a plain QWidget
   wrapping an internal child QLineEdit. Styling the outer QKeySequenceEdit
   directly (even just min-height) puts its own box model at odds with the
   inner one and clips the rendered text. The inner child already picks up
   the QLineEdit rule above on its own (it IS a QLineEdit), which is enough
   - leave the outer widget's height alone. */
QLabel[class="header"] {{
    font-size: {header}{ref_unit};
    font-weight: bold;
}}
QLabel[class="subheader"] {{
    font-weight: bold;
}}
QLabel[class="note"] {{
    font-size: {note}{ref_unit};
    font-style: italic;
}}
QLabel[class="muted"] {{
    font-size: {muted}{ref_unit};
    color: rgb(120, 120, 120);
}}
"""

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
    "label_40": "header",  # "Font size"
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
