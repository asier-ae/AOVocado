import json
import os
from pathlib import Path

MAIN_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))


class Settings:

    def __init__(self):
        settings_filepath = os.path.join(MAIN_FOLDER_PATH, "global_settings.json")
        self.UI_PATH = os.path.join(MAIN_FOLDER_PATH, "ui_files", "channelHubUI.ui")
        self.my_settings = self.load_settings(settings_filepath)
        self.CHANNELHUB_VERSION = "0.5"
        self.AUTHOR = "Asier Aparicio"
        self.HOTKEY = "Ctrl+`"
        self.GROUP1_SEARCH = self.my_settings["GROUP1_SEARCH"]
        self.GROUP2_SEARCH = self.my_settings["GROUP2_SEARCH"]
        self.GROUP3_SEARCH = self.my_settings["GROUP3_SEARCH"]
        self.GROUP1_TITLE = self.my_settings["GROUP1_TITLE"]
        self.GROUP2_TITLE = self.my_settings["GROUP2_TITLE"]
        self.GROUP3_TITLE = self.my_settings["GROUP3_TITLE"]
        self.GROUP4_TITLE = self.my_settings["GROUP4_TITLE"]

    def load_settings(self, filepath):
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"No such file: {filepath}")
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def get_version_line(self):
        return f"channelHub v{self.CHANNELHUB_VERSION}, {self.AUTHOR}"

    def get_hotkey_line(self):
        return f"{self.HOTKEY}: open and close panel"
