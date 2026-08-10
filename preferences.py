"""Generic, widget-driven save/load for the Settings window.

Works purely by widget type and object name - a widget named "cfg_main_h_sep"
in `preferencesUI.ui` is assumed to correspond to the JSON key
"cfg_main_h_sep" in `user_settings`, with no per-field mapping code needed.
This is deliberate: it means adding a new preference is just adding a widget
to the .ui with a matching object name and a default value in
`channelHub_global_settings.json` - nothing in this file needs to change.

Author: Asier Aparicio
"""

import json
import os

from . import logger
from ._vendor.Qt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

# Qt gives QSpinBox/QDoubleSpinBox an internal child QLineEdit with this
# fixed object name. findChildren(QLineEdit) picks it up even though it
# isn't one of our named preference widgets, so it must be filtered out
# wherever QLineEdit values are gathered.
_ROGUE_SPINBOX_LINEEDIT_NAME = "qt_spinbox_lineedit"

_log = logger.get_logger(__name__)

# Value getters, keyed by widget type, used when gathering current widget
# state to save. QPushButton is handled separately (see save_preferences)
# since only checkable ones (the mode toggles) represent a saved value.
_GETTERS = {
    QLineEdit: lambda w: w.text(),
    QCheckBox: lambda w: w.isChecked(),
    QDoubleSpinBox: lambda w: w.value(),
    QSpinBox: lambda w: w.value(),
    QComboBox: lambda w: w.currentText(),
}

# Value setters, keyed by widget type, used when applying loaded settings.
_SETTERS = {
    QLineEdit: lambda w, v: w.setText(v),
    QCheckBox: lambda w, v: w.setChecked(v),
    QDoubleSpinBox: lambda w, v: w.setValue(v),
    QSpinBox: lambda w, v: w.setValue(v),
    QComboBox: lambda w, v: w.setCurrentText(v),
    QPushButton: lambda w, v: w.setChecked(v) if w.isCheckable() else None,
}


def load_preferences(root_widget, user_settings):
    """Applies saved settings values onto the matching widgets by name.

    Args:
        root_widget (QWidget): The widget tree to search for named widgets
            (typically the Settings window itself).
        user_settings (dict): Mapping of widget object name to saved value,
            e.g. `settings.my_settings["user_settings"]`.
    """
    loaded_count = 0
    for object_name, value in user_settings.items():
        widget = root_widget.findChild(QWidget, object_name)
        if not widget:
            continue

        setter = _SETTERS.get(type(widget))
        if setter:
            setter(widget, value)
            loaded_count += 1
    _log.debug("load_preferences: applied %s of %s keys", loaded_count, len(user_settings))


def save_preferences(root_widget, filepath):
    """Gathers every known preference widget's current value and writes it out.

    Writes a full snapshot (not a diff) as `{"user_settings": {...}}` - this
    overwrites the entire file each time, so anything hand-added to it
    outside of a widget's value will not survive the next save.

    Args:
        root_widget (QWidget): The widget tree to search (typically the
            Settings window itself).
        filepath (str): Where to write the resulting JSON file.
    """
    user_settings = {}

    for widget_type, getter in _GETTERS.items():
        for widget in root_widget.findChildren(widget_type):
            object_name = widget.objectName()
            if not object_name or object_name == _ROGUE_SPINBOX_LINEEDIT_NAME:
                continue
            user_settings[object_name] = getter(widget)

    for button in root_widget.findChildren(QPushButton):
        object_name = button.objectName()
        if button.isCheckable() and object_name:
            user_settings[object_name] = button.isChecked()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"user_settings": user_settings}, f, indent=4)
    _log.debug("save_preferences: wrote %s keys to %s", len(user_settings), filepath)


def restore_default_preferences(filepath):
    """Deletes the user-override file, reverting to the base file's defaults.

    Args:
        filepath (str): Path to the user-override JSON file.
    """
    if os.path.isfile(filepath):
        os.remove(filepath)
        _log.debug("restore_default_preferences: removed %s", filepath)
    else:
        _log.debug("restore_default_preferences: no override file at %s", filepath)
