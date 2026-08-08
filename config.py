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
        self.HOTKEY = "Ctrl+`"
        self.LIST1_SEARCH = self.my_settings["LIST1_SEARCH"]
        self.LIST2_SEARCH = self.my_settings["LIST2_SEARCH"]
        self.LIST3_SEARCH = self.my_settings["LIST3_SEARCH"]
        self.LIST1_TITLE = self.my_settings["LIST1_TITLE"]
        self.LIST2_TITLE = self.my_settings["LIST2_TITLE"]
        self.LIST3_TITLE = self.my_settings["LIST3_TITLE"]
        self.LIST4_TITLE = self.my_settings["LIST4_TITLE"]

    def load_settings(self, filepath):
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"No such file: {filepath}")
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
