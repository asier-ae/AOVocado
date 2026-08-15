"""Tooltip text for the Settings window's widgets.

Plain `{object_name: tooltip text}` data, applied generically by
`apply_tooltips()` - matches `settings_io.py`'s own object-name-driven
pattern. Scoped to `settings_window.py`/`preferencesUI.ui` only; the main
panel sets its own tooltips inline where it has one (`utils.set_button_icon`'s
`tooltip` param, `live_sampler_controller.py`).

Author: Asier Aparicio
"""

from ._vendor.Qt.QtWidgets import QWidget

_GENERAL = {
    "cfg_hotkey": "Keyboard shortcut that opens and closes the main panel. "
    "Press a key combo to set it - takes effect the next time Nuke is launched.",
    "cfg_sp_sampler_threshold": "Minimum pixel value for the live sampler "
    "to treat a channel as active.",
    "cfg_main_h_sep": "Horizontal pixel spacing between nodes when creating in horizontal mode.",
    "cfg_main_v_sep": "Vertical pixel spacing between nodes when creating in vertical mode.",
}

# Applied to BUTTON1_*..BUTTON4_* via the suffix, same text for every button.
_BUTTON_FIELD_TOOLTIPS = {
    "_TITLE": "Text shown on this button in the main panel.",
    "_SOURCE": "Where this button creates nodes from: a registered Node "
    "class, or a standalone toolset/group Nuke script.",
    "_CLASS": "A node class name (e.g. Shuffle2), or the path to a "
    "toolset/group .nk file - depending on Source above.",
    "_KNOB": "Name of the knob on the created node that gets set to the selected channel.",
    "_ICONMODE": "Default node-creation layout for this button: unchecked "
    "= vertical stack, checked = horizontal row.",
}

_REBUILD_SUBTRACTIVE = {
    "cfg_rs_cb_rebuild_layout": "Which side the subtractive rebuild's branches build out to.",
    "cfg_rs_spb_h_sep_main": "Horizontal spacing between each channel's branch.",
    "cfg_rs_spb_v_sep_base": "Vertical spacing around the base isolate/subtract nodes.",
    "cfg_rs_spb_v_sep_grade": "Vertical spacing around the grading nodes.",
    "cfg_rs_spb_bd_sep_top": "Backdrop margin above the nodes.",
    "cfg_rs_spb_bd_sep_bottom": "Backdrop margin below the nodes.",
    "cfg_rs_spb_bd_sep_left": "Backdrop margin to the left of the nodes.",
    "cfg_rs_spb_bd_sep_right": "Backdrop margin to the right of the nodes.",
}

_BOTTOM_BUTTONS = {
    "b_saveprefs": "Save these settings. Changes take effect the next "
    "time the main panel is opened.",
    "b_saveprefsclose": "Save these settings and close this window.",
    "b_restoreprefs": "Delete your saved overrides and reset every setting back to its default.",
}


def _build_tooltips():
    """Assembles the full object-name-to-tooltip-text mapping.

    Returns:
        dict[str, str]: Tooltip text keyed by widget object name.
    """
    tooltips = {}
    tooltips.update(_GENERAL)
    tooltips.update(_REBUILD_SUBTRACTIVE)
    tooltips.update(_BOTTOM_BUTTONS)
    for i in range(1, 5):
        for suffix, text in _BUTTON_FIELD_TOOLTIPS.items():
            tooltips[f"BUTTON{i}{suffix}"] = text
    return tooltips


TOOLTIPS = _build_tooltips()


def apply_tooltips(root_widget):
    """Sets a tooltip on every widget in `root_widget` that TOOLTIPS names.

    Args:
        root_widget (QWidget): The widget tree to search (typically the
            Settings window itself).
    """
    for object_name, text in TOOLTIPS.items():
        widget = root_widget.findChild(QWidget, object_name)
        if widget:
            widget.setToolTip(text)
