"""Everything related to the Nuke viewer: the ViewerManager interface, and
reacting to the active viewer's connected input changing.

Author: Asier Aparicio
"""

import nuke

from . import constants, logger, utils

_log = logger.get_logger(__name__)

# Callback code Nuke executes via the viewer's knobChanged knob - an
# absolute import since Nuke runs this in its own scope, not as part of
# this package. See ViewerManager.enable_reload_callback() and
# viewer_updated() below.
_RELOAD_CALLBACK_CODE = "from channelHub import viewer; viewer.viewer_updated()"


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

        This fully overwrites the viewer's knobChanged value rather than
        composing with anything already set there, so whatever calls this
        needs to own that knob exclusively - which is why `remove_callback()`
        below is called on panel close, not left set indefinitely.

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

    @staticmethod
    def enable_reload_callback():
        """Sets `viewer_updated()` as the active viewer's knobChanged callback.

        Called by `ChannelHub._setup_viewer_callback()` so the panel reloads
        when the viewer's connected input changes.
        """
        ViewerManager.add_callback(_RELOAD_CALLBACK_CODE)


def viewer_updated():
    """Reloads the open panel's channel lists when the viewer's input changes.

    Set as a `knobChanged` callback on the active viewer by
    `ViewerManager.enable_reload_callback()`. Nuke executes this in the
    viewer node's own callback context (`nuke.thisNode()`/`nuke.thisKnob()`)
    - only "inputChange"/"input_number" knob changes (the viewer's connected
    input actually changing) should trigger a reload; everything else is a
    no-op.
    """
    viewer_node = nuke.thisNode()
    try:
        # Guards against a stale/detached node context - can happen if this
        # fires while Nuke is mid-teardown of the viewer node.
        viewer_node.name()
    except Exception:
        return

    knob = nuke.thisKnob()
    knob_name = knob.name() if knob else None
    if not knob or knob_name not in ("inputChange", "input_number"):
        _log.debug("knobChanged fired for %s - ignored", knob_name)
        return

    _log.debug("knobChanged fired for %s - reloading panel", knob_name)
    panel = utils.find_window_by_title(constants.QWINDOW_TITLE)
    if panel:
        panel.reload_channels()
