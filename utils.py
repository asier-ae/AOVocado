"""Small standalone UI helpers for channelHub.

Author: Asier Aparicio
"""

from ._vendor.Qt.QtGui import QCursor


def _move_to_cursor(main_window):
    """Positions a window centered on the current mouse cursor location.

    Args:
        main_window (QWidget): The window to move. Its current size() is
            used to compute the centering offset (integer division is
            intentional - sub-pixel window positions aren't meaningful).
    """
    cursor_pos = QCursor().pos()
    window_size = main_window.size()
    main_window.move(
        cursor_pos.x() - window_size.width() // 2,
        cursor_pos.y() - window_size.height() // 2,
    )
