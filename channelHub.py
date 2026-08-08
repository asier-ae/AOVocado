from . import config, constants
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import Qt
from ._vendor.Qt.QtGui import QCursor
from ._vendor.Qt.QtWidgets import QMainWindow


class ChannelHub(QMainWindow):
    """Main panel window for viewing and managing AOV render channels."""

    def __init__(self):
        super().__init__()
        self.settings = config.Settings()
        self._initial_window_setup()

    def _initial_window_setup(self):
        """Loads the UI file and configures the main window's properties."""
        self.ui = loadUi(self.settings.UI_PATH, self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(constants.QWINDOW_TITLE)
        self.installEventFilter(self)
        self._move_to_cursor()

    def _move_to_cursor(self):
        """Positions the window near the current mouse cursor location."""
        cursor_pos = QCursor().pos()
        window_size = self.size()
        self.move(
            cursor_pos.x() - window_size.width() // 2,
            cursor_pos.y() - window_size.height() // 2,
        )
