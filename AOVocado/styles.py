# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Centralized QSS styling for both AOVocado windows.

Replaces per-widget `pointsize`/`bold` properties scattered across the two
`.ui` files with one stylesheet applied via `setStyleSheet()`, plus a small
`class` dynamic property on the few widgets that need to deviate from the
base look (section headers, sub-headers, the one note, the one muted
label). No font-family is set anywhere here, deliberately - every widget
keeps inheriting Nuke's own default Qt font for the current OS, so text
stays visually consistent with the rest of Nuke's interface rather than
introducing a font that might not even be installed on a given machine.
"""

from ._vendor.Qt.QtWidgets import QWidget

STYLESHEET = """
QWidget {
    font-size: 12pt;
}
QGroupBox {
    font-weight: bold;
}
QLabel[class="header"] {
    font-size: 13pt;
    font-weight: bold;
}
QLabel[class="subheader"] {
    font-weight: bold;
}
QLabel[class="note"] {
    font-size: 11pt;
    font-style: italic;
}
QLabel[class="muted"] {
    font-size: 10pt;
    color: rgb(120, 120, 120);
}
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
