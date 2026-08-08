from ._vendor.Qt.QtGui import QCursor


def _move_to_cursor(main_window):
    """Positions the window near the current mouse cursor location."""
    cursor_pos = QCursor().pos()
    window_size = main_window.size()
    main_window.move(
        cursor_pos.x() - window_size.width() // 2,
        cursor_pos.y() - window_size.height() // 2,
    )
