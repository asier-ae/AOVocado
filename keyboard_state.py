"""Tracks Ctrl/Shift modifier state to drive multi-select mode.

Author: Asier Aparicio
"""

from ._vendor.Qt.QtCore import Qt


class KeyboardState:
    """Manages the state of modifier keys for multi-selection.

    Attributes:
        ctrl_pressed (bool): True if the Control key is currently pressed.
        shift_pressed (bool): True if the Shift key is currently pressed.
    """

    def __init__(self):
        """Initializes the KeyboardState with keys in the released state."""
        self.ctrl_pressed = False
        self.shift_pressed = False

    @property
    def multi_selection_active(self):
        """Checks if multi-selection keys (Ctrl or Shift) are active.

        Returns:
            bool: True if either Ctrl or Shift is pressed, False otherwise.
        """
        return self.ctrl_pressed or self.shift_pressed

    def update_key_press(self, key):
        """Updates the state when a key is pressed.

        Args:
            key (Qt.Key): The key that was pressed.
        """
        if key == Qt.Key_Control:
            self.ctrl_pressed = True
        elif key == Qt.Key_Shift:
            self.shift_pressed = True

    def update_key_release(self, key):
        """Updates the state when a key is released.

        Args:
            key (Qt.Key): The key that was released.
        """
        if key == Qt.Key_Control:
            self.ctrl_pressed = False
        elif key == Qt.Key_Shift:
            self.shift_pressed = False

    def reset(self):
        """Resets all key states to released."""
        self.ctrl_pressed = False
        self.shift_pressed = False
