"""Entry point for launching/closing the channelHub panel.

Author: Asier Aparicio
"""

import nuke

from . import constants
from ._vendor.Qt.QtWidgets import QApplication
from .channelHub import ChannelHub


def run():
    """Opens the channelHub panel, or closes it if already open.

    Intended to be called from a Nuke menu command/hotkey. Guards on having
    a Viewer with a connected input, since ChannelManager needs a valid
    viewer input node to collect channels from.

    channelHub isn't a native Nuke panel/pane, so there's no built-in
    open/closed state to query. Instead, "is it open" is tracked via a
    dynamic `nuke.<NUKE_PANEL_NAME>` attribute, and closing is done by
    scanning `QApplication.topLevelWidgets()` for a window with a matching
    title - there's no persistent Python reference to the panel between
    separate hotkey presses without this, since each press is a fresh call
    to this function.
    """
    if not nuke.allNodes("Viewer"):
        nuke.message("Please create a viewer first.")
        return

    if nuke.activeViewer().activeInput() is None:
        nuke.message("Please connect a viewer input.")
        return

    is_panel_open = getattr(nuke, constants.NUKE_PANEL_NAME, False)
    if is_panel_open:
        for widget in QApplication.topLevelWidgets():
            if widget.windowTitle() == constants.QWINDOW_TITLE:
                widget.close()
                break
    else:
        setattr(nuke, constants.NUKE_PANEL_NAME, True)
        panel_instance = ChannelHub()
        constants.GC_PROTECT.append(panel_instance)
        panel_instance.show()
