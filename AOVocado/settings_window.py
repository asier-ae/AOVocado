# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""The Settings window for AOVocado.

Loads `ui_files/preferencesUI.ui` and wires it to the generic load/save/
restore functions in `settings_io.py`. Every field here is functional -
node-creation buttons/spacing, the live sampler threshold
(`live_sampler.py`), and the "Rebuild Subtractive" tab (`rebuild_subtractive.py`).
"""

from . import config, logger, node_creation, settings_io, settings_tooltips, utils
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import Qt
from ._vendor.Qt.QtGui import QKeySequence
from ._vendor.Qt.QtWidgets import QMainWindow, QMessageBox

_log = logger.get_logger(__name__)


class SettingsWindow(QMainWindow):
    """A standalone window for editing and persisting AOVocado's preferences.

    `AOVocado.py`'s `_on_show_settings` closes the main panel when opening
    this window, rather than leaving both open - the main panel reads
    settings once at construction, so it wouldn't reflect any changes made
    here until reopened anyway.

    Attributes:
        settings (config.Settings): The settings this window is editing.
    """

    # Object names of the 4 node-creation mode toggle buttons in
    # preferencesUI.ui - the settings-window equivalent of AOVocado.py's
    # b1_mode..b4_mode, but these set the *persisted default* rather than
    # the live in-session mode.
    MODE_BUTTONS = [
        "BUTTON1_ICONMODE",
        "BUTTON2_ICONMODE",
        "BUTTON3_ICONMODE",
        "BUTTON4_ICONMODE",
    ]

    def __init__(self):
        """Loads settings, builds the window, and populates it from them."""
        _log.debug("SettingsWindow opening")
        super().__init__()
        self.settings = config.Settings()

        self._setup_window()
        self._setup_about_tab()
        self._setup_mode_buttons()
        self._load_settings_to_ui()
        self._connect_signals()

    def _setup_window(self):
        """Loads the UI file and configures the window's properties."""
        loadUi(self.settings.PREFERENCES_UI_PATH, self)
        self.setWindowTitle("AOVocado Settings")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        settings_tooltips.apply_tooltips(self)

    def _setup_about_tab(self):
        """Populates the About tab's title/version, info, and shortcuts labels."""
        self.lb_title_version.setText(self.settings.get_copyright_line())
        self.lb_info_text.setText(self.settings.get_info_text())
        self.lb_shortcuts_text.setText(self.settings.get_shortcuts_text())

    def _setup_mode_buttons(self):
        """Configures the 4 mode-toggle buttons' icon and text."""
        for button_name in self.MODE_BUTTONS:
            button = getattr(self, button_name)
            button.setText("")
            button.toggled.connect(
                lambda checked, b=button: self._update_mode_button(b)
            )

    def _update_mode_button(self, button):
        """Refreshes one mode button's icon/tooltip to match its checked state.

        Args:
            button (QPushButton): The mode button that changed.
        """
        utils.update_mode_button_visuals(
            button, self.settings.ICON_H_MODE, self.settings.ICON_V_MODE
        )

    def _load_settings_to_ui(self):
        """Applies the currently loaded settings onto every matching widget."""
        settings_io.load_preferences(self, self.settings.my_settings["user_settings"])
        for button_name in self.MODE_BUTTONS:
            self._update_mode_button(getattr(self, button_name))

    def _connect_signals(self):
        """Connects the Save/Save & Close/Restore buttons to their handlers."""
        self.b_saveprefs.clicked.connect(self._on_save_preferences)
        self.b_saveprefsclose.clicked.connect(self._on_save_and_close)
        self.b_restoreprefs.clicked.connect(self._on_restore_preferences)
        self.cfg_hotkey.keySequenceChanged.connect(self._on_hotkey_changed)

    def _on_hotkey_changed(self, key_sequence):
        """Keeps the hotkey field to a single key combo, not a multi-chord sequence.

        QKeySequenceEdit accepts up to 4 chained key presses by default
        (e.g. "Ctrl+K, Ctrl+D") - AOVocado/Nuke hotkeys are always a
        single combo, so anything past the first chord is dropped
        immediately. String-based rather than indexing into the
        QKeySequence, since that API differs between the Qt5/Qt6 bindings
        this codebase supports.

        Args:
            key_sequence (QKeySequence): The field's new key sequence.
        """
        text = key_sequence.toString(QKeySequence.PortableText)
        first_chord = text.split(",")[0].strip()
        if first_chord != text:
            self.cfg_hotkey.setKeySequence(QKeySequence(first_chord))

    def _validate_toolset_settings(self):
        """Checks every button configured to paste a toolset has a usable path.

        Returns:
            list[str]: One message per BUTTON1..4 whose Source is set to
                "Nuke script path" but whose path isn't currently a usable
                single-node toolset (see `utils.validate_toolset_path()`).
                Empty if everything's fine.
        """
        problems = []
        for i in range(1, 5):
            source = getattr(self, f"BUTTON{i}_SOURCE").currentText()
            if source != node_creation.SOURCE_TOOLSET:
                continue
            path = getattr(self, f"BUTTON{i}_CLASS").text()
            reason = utils.validate_toolset_path(path)
            if reason:
                title = getattr(self, f"BUTTON{i}_TITLE").text()
                problems.append(f'BUTTON{i} ("{title}"): {reason}')
        return problems

    def _save_preferences(self):
        """Writes every preference widget's current value to the user-override file.

        Blocked (nothing written) if any button set to "Nuke script path"
        doesn't currently point at a usable single-node toolset - see
        `_validate_toolset_settings()`.

        Returns:
            bool: True if the save went through, False if it was blocked.
        """
        problems = self._validate_toolset_settings()
        if problems:
            _log.debug("save blocked: %s", problems)
            QMessageBox.warning(
                self,
                "Invalid Toolset Path",
                "Fix the following before saving:\n\n" + "\n".join(problems),
            )
            return False

        settings_io.save_preferences(self, self.settings.USER_SETTINGS_PATH)
        return True

    def _on_save_preferences(self):
        """Saves preferences and confirms, without closing the window.

        Returns:
            bool: True if the save went through, False if it was blocked.
        """
        _log.debug("Save Settings clicked")
        if not self._save_preferences():
            return False
        QMessageBox.information(
            self,
            "Save Settings",
            f"Settings saved to:\n{self.settings.USER_SETTINGS_PATH}\n\n"
            "Changes will apply the next time the main panel is opened.",
        )
        return True

    def _on_save_and_close(self):
        """Saves preferences and closes the window, unless the save was blocked.

        No confirmation dialog here (unlike `_on_save_preferences`) - the
        window closing is itself the feedback that the save went through.
        Stays open if the save was blocked, so an invalid toolset path can
        be fixed and retried.
        """
        _log.debug("Save & Close clicked")
        if self._on_save_preferences():
            self.close()

    def _on_restore_preferences(self):
        """Deletes the user-override file and reloads defaults, after confirming."""
        confirm = QMessageBox.question(
            self,
            "Restore Defaults",
            "Reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        _log.debug("Restore Defaults confirmed")
        settings_io.restore_default_preferences(self.settings.USER_SETTINGS_PATH)
        self.settings = config.Settings()
        self._load_settings_to_ui()
        QMessageBox.information(
            self, "Restore Defaults", "Settings restored to defaults."
        )
