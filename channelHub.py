import nuke

from . import config, constants, utils
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import Qt
from ._vendor.Qt.QtWidgets import QMainWindow


class ChannelHub(QMainWindow):

    def __init__(self):
        super().__init__()
        self.settings = config.Settings()
        self._initial_window_setup()

    def _initial_window_setup(self):
        """Loads the UI file and configures the main window's properties."""
        loadUi(self.settings.UI_PATH, self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(constants.QWINDOW_TITLE)
        utils._move_to_cursor(self)

    def closeEvent(self, event):
        # sets the nuke flag to closed
        setattr(nuke, constants.NUKE_PANEL_NAME, False)
