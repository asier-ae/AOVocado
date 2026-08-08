import os

MAIN_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))


class Settings:

    def __init__(self):
        self.CHANNELHUB_VERSION = "0.5"
        self.HOTKEY = "Ctrl+`"
        self.UI_PATH = os.path.join(MAIN_FOLDER_PATH, "ui_files", "channelHubUI.ui")
