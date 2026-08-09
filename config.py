"""Application settings for channelHub.

Loads `channelHub_global_settings.json` (plus an optional user-override
file) and exposes its values as attributes on a single `Settings` object,
along with a couple of derived display strings.

Author: Asier Aparicio
"""

import json
import os
from pathlib import Path

MAIN_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))


class Settings:
    """Loads and exposes channelHub's configuration.

    Settings come from two layered JSON files:

    - The base file, `channelHub_global_settings.json`, ships with the tool
      (next to this module) and is never written to by the tool itself.
    - An optional user-override file, `~/.nuke/channelHub_user_settings.json`
      (deliberately outside this repo, directly under the Nuke prefs root -
      not `~/.nuke/python/channelHub/`, so it survives a reinstall of the
      tool itself, and is prefixed `channelHub_` since `~/.nuke/` is shared
      with the user's other tools). If present, its `user_settings` keys are
      shallow-merged on top of the base file's `user_settings` block - keys
      it doesn't mention keep falling back to the base file's values. Only
      `user_settings` is layered this way; GROUP*/HOTKEY are base-file-only.
      Written by `preferences.save_preferences()` (see `settings_window.py`);
      deleting it (`preferences.restore_default_preferences()`) reverts
      everything in `user_settings` back to the base file's values.

    Attributes:
        UI_PATH (str): Absolute path to the main panel's .ui file.
        PREFERENCES_UI_PATH (str): Absolute path to the Settings window's .ui file.
        USER_SETTINGS_PATH (str): Path to the user-override JSON file (see above).
        my_settings (dict): The parsed base settings, with any user-override
            `user_settings` values merged in.
        CHANNELHUB_VERSION (str): Current tool version, shown in the panel.
        AUTHOR (str): Tool author, shown in the panel.
        HOTKEY (str): Keyboard shortcut that opens/closes the panel.
        GROUP1_SEARCH (list[str]): Group 1 exact-match channel names.
        GROUP2_SEARCH (list[str]): Group 2 prefix-match strings.
        GROUP3_SEARCH (list[str]): Group 3 exact-match channel names.
        GROUP1_TITLE (str): Group 1 display title.
        GROUP2_TITLE (str): Group 2 display title.
        GROUP3_TITLE (str): Group 3 display title.
        GROUP4_TITLE (str): Group 4 (catch-all) display title.
        ICON_H_MODE (str): Path to the horizontal node-creation-mode icon.
        ICON_V_MODE (str): Path to the vertical node-creation-mode icon.
        ICON_SETTINGS (str): Path to the settings-button icon.
        ICON_COPY (str): Path to the copy-to-clipboard button icon.
        ICON_SAMPLE (str): Path to the live-sampler button icon (idle state).
        ICON_SAMPLE_WHITE (str): Path to the live-sampler button icon
            (active/sampling state).
        ICON_SPLIT_SUBTRACTIVE (str): Path to the subtractive-rebuild
            button icon.
        BACKDROP_TILE_COLOR (int): Rebuild-backdrop fill color.
        BACKDROP_APPEARANCE (str): Rebuild-backdrop appearance style.
        BACKDROP_BORDER_WIDTH (int): Rebuild-backdrop border thickness.
        BACKDROP_FONT_COLOR (int): Rebuild-backdrop label text color.
        BACKDROP_FONT_SIZE (int): Rebuild-backdrop label text size.
    """

    def __init__(self):
        """Loads settings (base + user override) and populates all attributes.

        Raises:
            FileNotFoundError: If the base settings file is missing. This is
                intentional - failing fast here is preferable to silently
                falling back to empty group lists, which would open the
                panel with 4 blank lists and no obvious reason why. The
                user-override file, by contrast, is genuinely optional (most
                users won't have customized anything yet) and its absence is
                not an error.
        """
        self.CHANNELHUB_VERSION = "0.5"
        self.AUTHOR = "Asier Aparicio"
        # self.HOTKEY = self.my_settings["HOTKEY"]
        self.HOTKEY = "hotkey"
        base_filepath = os.path.join(
            MAIN_FOLDER_PATH, "channelHub_global_settings.json"
        )
        self.UI_PATH = os.path.join(MAIN_FOLDER_PATH, "ui_files", "channelHubUI.ui")
        self.PREFERENCES_UI_PATH = os.path.join(
            MAIN_FOLDER_PATH, "ui_files", "preferencesUI.ui"
        )
        self.USER_SETTINGS_PATH = os.path.join(
            os.path.expanduser("~"), ".nuke", "channelHub_user_settings.json"
        )

        self.my_settings = self.load_settings(base_filepath)

        self._apply_user_overrides()
        self._load_groups()
        self._load_icons()
        self._load_backdrop_style()

    def _load_groups(self):
        self.GROUP1_SEARCH = self.my_settings["GROUP1_SEARCH"]
        self.GROUP2_SEARCH = self.my_settings["GROUP2_SEARCH"]
        self.GROUP3_SEARCH = self.my_settings["GROUP3_SEARCH"]
        self.GROUP1_TITLE = self.my_settings["GROUP1_TITLE"]
        self.GROUP2_TITLE = self.my_settings["GROUP2_TITLE"]
        self.GROUP3_TITLE = self.my_settings["GROUP3_TITLE"]
        self.GROUP4_TITLE = self.my_settings["GROUP4_TITLE"]

    def _load_icons(self):
        self.ICON_H_MODE = os.path.join(MAIN_FOLDER_PATH, "icons", "h_mode.png")
        self.ICON_V_MODE = os.path.join(MAIN_FOLDER_PATH, "icons", "v_mode.png")
        self.ICON_SETTINGS = os.path.join(MAIN_FOLDER_PATH, "icons", "cogs.png")
        self.ICON_COPY = os.path.join(MAIN_FOLDER_PATH, "icons", "copy.png")
        self.ICON_SAMPLE = os.path.join(MAIN_FOLDER_PATH, "icons", "sample.png")
        self.ICON_SAMPLE_WHITE = os.path.join(
            MAIN_FOLDER_PATH, "icons", "sample_white.png"
        )
        self.ICON_SPLIT_SUBTRACTIVE = os.path.join(
            MAIN_FOLDER_PATH, "icons", "splitlayers_subtractive.png"
        )

    def _load_backdrop_style(self):
        self.BACKDROP_TILE_COLOR = self.my_settings["BACKDROP_TILE_COLOR"]
        self.BACKDROP_APPEARANCE = self.my_settings["BACKDROP_APPEARANCE"]
        self.BACKDROP_BORDER_WIDTH = self.my_settings["BACKDROP_BORDER_WIDTH"]
        self.BACKDROP_FONT_COLOR = self.my_settings["BACKDROP_FONT_COLOR"]
        self.BACKDROP_FONT_SIZE = self.my_settings["BACKDROP_FONT_SIZE"]

    def load_settings(self, filepath):
        """Reads and parses a JSON settings file.

        Args:
            filepath (str): Path to the JSON file to load.

        Returns:
            dict: The parsed JSON contents.

        Raises:
            FileNotFoundError: If filepath does not exist.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"No such file: {filepath}")
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def _apply_user_overrides(self):
        """Shallow-merges the user-override file's `user_settings` onto the base's.

        No-op if the override file doesn't exist yet (nothing saved so far)
        or doesn't contain a `user_settings` block.
        """
        if not os.path.exists(self.USER_SETTINGS_PATH):
            return
        user_overrides = self.load_settings(self.USER_SETTINGS_PATH)
        self.my_settings.setdefault("user_settings", {}).update(
            user_overrides.get("user_settings", {})
        )

    def get_version_line(self):
        """Builds the version/author line shown in the panel's bottom bar.

        Returns:
            str: e.g. "channelHub v0.5, Asier Aparicio".
        """
        return f"channelHub v{self.CHANNELHUB_VERSION}, {self.AUTHOR}"

    def get_hotkey_line(self):
        """Builds the hotkey hint line shown in the panel's bottom bar.

        Returns:
            str: e.g. "Ctrl+`: open and close panel".
        """
        return f"{self.HOTKEY}: open and close panel"
