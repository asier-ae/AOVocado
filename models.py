import nuke

from ._vendor.Qt.QtCore import Qt


class ChannelGroups:

    def __init__(self):

        self.group_ch1 = []
        self.group_ch2 = []
        self.group_ch3 = []
        self.group_ch4 = []

    def clear(self):

        self.group_ch1.clear()
        self.group_ch2.clear()
        self.group_ch3.clear()
        self.group_ch4.clear()


class ChannelManager:

    def __init__(self, config):
        """Initializes the ChannelManager with application settings.

        Args:
            config (Settings): The application settings object.
        """
        self.settings = config
        self.group1_set = {x.lower() for x in self.settings.GROUP1_SEARCH}
        # Prefixes need to be a tuple for .startswith()
        self.group2_prefixes = tuple(self.settings.GROUP2_SEARCH)
        self.group3_set = {x.lower() for x in self.settings.GROUP3_SEARCH}

    def categorize_channels(self, channel_list):
        """Categorizes a list of channels into predefined groups.

        Args:
            channel_list (list[str]): A list of full channel names (e.g., 'rgba.red').

        Returns:
            ChannelGroups: An object containing categorized lists of channel layers.
        """
        groups = ChannelGroups()

        # Extract unique channel names (before the dot)
        unique_channels = sorted(
            set(c.split(".")[0] for c in channel_list), key=lambda v: v.upper()
        )

        # Categorize channels based on configuration
        for channel in unique_channels:
            channel_lower = channel.lower()

            if channel_lower in self.group1_set:
                groups.group_ch1.append(channel)
            elif channel_lower in self.group3_set:
                groups.group_ch3.append(channel)
            # .startswith can accept a tuple of prefixes
            elif channel.startswith(self.group2_prefixes):
                groups.group_ch2.append(channel)
            else:
                groups.group_ch4.append(channel)

        return groups

    def collect_channels_from_viewer(self):
        """Collects and categorizes channels from the active viewer's input.

        Returns:
            ChannelGroups: An object containing the categorized channels.
        """
        viewer_input_node = ViewerManager.get_viewer_input_node()
        if not viewer_input_node:
            return ChannelGroups()

        all_channels = viewer_input_node.channels()
        return self.categorize_channels(all_channels)


class ViewerManager:
    """Provides an interface for interacting with the Nuke viewer.

    This class contains static methods to get and set viewer properties and
    to manage viewer callbacks.
    """

    @staticmethod
    def get_active_viewer():
        """Gets the active viewer node in Nuke.

        Returns:
            nuke.Node or None: The active viewer node, or None if not found.
        """
        return nuke.activeViewer().node()

    @staticmethod
    def get_viewer_channel():
        """Gets the channel currently displayed in the active viewer.

        Returns:
            str: The name of the currently displayed channel.
        """
        return nuke.activeViewer().node()["channels"].value()

    @staticmethod
    def set_viewer_channel(channel):
        """Sets the active viewer to display a specific channel.

        Args:
            channel (str): The name of the channel to display.
        """
        ViewerManager.get_active_viewer().knob("channels").setValue(channel)

    @staticmethod
    def get_viewer_input_node():
        """Gets the node connected to the active viewer input.

        Returns:
            nuke.Node or None: The node connected to the viewer, or None.
        """
        viewer = nuke.activeViewer()
        viewer_node = viewer.node()
        active_buffer = viewer.activeInput()
        return viewer_node.input(active_buffer)

    @staticmethod
    def add_callback(callback_code):
        """Adds a Python callback to the active viewer's knobChanged knob.

        Args:
            callback_code (str): The Python code to execute as the callback.
        """
        viewer_node = ViewerManager.get_active_viewer()
        viewer_node["knobChanged"].setValue(callback_code)

    @staticmethod
    def remove_callback():
        """Removes the knobChanged callback from the active viewer."""
        viewer_node = ViewerManager.get_active_viewer()
        viewer_node["knobChanged"].setValue("")


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
