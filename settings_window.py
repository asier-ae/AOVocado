"""The Settings window for channelHub.

Loads `ui_files/preferencesUI.ui` and wires it to the generic load/save/
restore functions in `preferences.py`. Every field here is functional -
node-creation buttons/spacing, the live sampler threshold
(`live_sampler.py`), and the "Rebuild Substractive" tab (`rebuild_subtractive.py`).

Author: Asier Aparicio
"""

from . import config, logger, preferences, utils
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import Qt
from ._vendor.Qt.QtWidgets import QMainWindow, QMessageBox

_log = logger.get_logger(__name__)


class SettingsWindow(QMainWindow):
    """A standalone window for editing and persisting channelHub's preferences.

    `channelHub.py`'s `_on_show_settings` closes the main panel when opening
    this window, rather than leaving both open - the main panel reads
    settings once at construction, so it wouldn't reflect any changes made
    here until reopened anyway.

    Attributes:
        settings (config.Settings): The settings this window is editing.
    """

    # Object names of the 4 node-creation mode toggle buttons in
    # preferencesUI.ui - the settings-window equivalent of channelHub.py's
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
        self._setup_mode_buttons()
        self._load_settings_to_ui()
        self._connect_signals()

    def _setup_window(self):
        """Loads the UI file and configures the window's properties."""
        loadUi(self.settings.PREFERENCES_UI_PATH, self)
        self.setWindowTitle("channelHub Settings")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

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
        preferences.load_preferences(self, self.settings.my_settings["user_settings"])
        for button_name in self.MODE_BUTTONS:
            self._update_mode_button(getattr(self, button_name))

    def _connect_signals(self):
        """Connects the Save/Save & Close/Restore buttons to their handlers."""
        self.b_saveprefs.clicked.connect(self._on_save_preferences)
        self.b_saveprefsclose.clicked.connect(self._on_save_and_close)
        self.b_restoreprefs.clicked.connect(self._on_restore_preferences)

    def _save_preferences(self):
        """Writes every preference widget's current value to the user-override file."""
        preferences.save_preferences(self, self.settings.USER_SETTINGS_PATH)

    def _on_save_preferences(self):
        """Saves preferences and confirms, without closing the window."""
        _log.debug("Save Settings clicked")
        self._save_preferences()
        QMessageBox.information(
            self,
            "Save Settings",
            f"Settings saved to:\n{self.settings.USER_SETTINGS_PATH}\n\n"
            "Changes will apply the next time the main panel is opened.",
        )

    def _on_save_and_close(self):
        """Saves preferences and closes the window.

        No confirmation dialog here (unlike `_on_save_preferences`) - the
        window closing is itself the feedback that the save went through.
        """
        _log.debug("Save & Close clicked")
        self._on_save_preferences()
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
        preferences.restore_default_preferences(self.settings.USER_SETTINGS_PATH)
        self.settings = config.Settings()
        self._load_settings_to_ui()
        QMessageBox.information(
            self, "Restore Defaults", "Settings restored to defaults."
        )
