"""Application settings for channelHub.

Loads `global_settings.json` and exposes its values as attributes on a
single `Settings` object, along with a couple of derived display strings.

Author: Asier Aparicio
"""

import json
import os
from pathlib import Path

MAIN_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))


class Settings:
    """Loads and exposes channelHub's configuration.

    Attributes:
        UI_PATH (str): Absolute path to the .ui file loaded by ChannelHub.
        my_settings (dict): The raw parsed contents of
            global_settings.json, including the still-unconsumed
            `user_settings` sub-block (button-to-node-class mappings,
            rebuild-panel layout, sampler threshold, etc.). Intentionally
            not yet promoted into named attributes - what shape it needs is
            deferred until the features that consume it (node-creation
            buttons, rebuild panel, sampler, settings window) are built.
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
    """

    def __init__(self):
        """Loads global_settings.json and populates all settings attributes.

        Raises:
            FileNotFoundError: If global_settings.json is missing. This is
                intentional - failing fast here is preferable to silently
                falling back to empty group lists, which would open the
                panel with 4 blank lists and no obvious reason why.
        """
        settings_filepath = os.path.join(MAIN_FOLDER_PATH, "global_settings.json")
        self.UI_PATH = os.path.join(MAIN_FOLDER_PATH, "ui_files", "channelHubUI.ui")
        self.my_settings = self.load_settings(settings_filepath)
        self.CHANNELHUB_VERSION = "0.5"
        self.AUTHOR = "Asier Aparicio"
        # self.HOTKEY = self.my_settings["HOTKEY"]
        self.HOTKEY = "hotkey"
        self.GROUP1_SEARCH = self.my_settings["GROUP1_SEARCH"]
        self.GROUP2_SEARCH = self.my_settings["GROUP2_SEARCH"]
        self.GROUP3_SEARCH = self.my_settings["GROUP3_SEARCH"]
        self.GROUP1_TITLE = self.my_settings["GROUP1_TITLE"]
        self.GROUP2_TITLE = self.my_settings["GROUP2_TITLE"]
        self.GROUP3_TITLE = self.my_settings["GROUP3_TITLE"]
        self.GROUP4_TITLE = self.my_settings["GROUP4_TITLE"]

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
