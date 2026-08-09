"""Entry point for opening/closing the channelHub panel.

Author: Asier Aparicio
"""

import nuke

from . import constants, utils
from .channelHub import ChannelHub


def run():
    """Opens the channelHub panel, or closes it if already open.

    Intended to be called from a Nuke menu command/hotkey. Guards on having
    a Viewer with a connected input, since ChannelManager needs a valid
    viewer input node to collect channels from.

    channelHub isn't a native Nuke panel/pane, so there's no built-in
    open/closed state to query. Instead, "is it open" is tracked via a
    dynamic `nuke.<NUKE_PANEL_NAME>` attribute, and closing is done via
    `utils.find_window_by_title()` - there's no persistent Python reference
    to the panel between separate hotkey presses without this, since each
    press is a fresh call to this function.
    """
    if nuke.NUKE_VERSION_MAJOR < constants.MIN_NUKE_VERSION:
        nuke.message(
            f"channelHub requires Nuke {constants.MIN_NUKE_VERSION}+ "
            f"(this is Nuke {nuke.NUKE_VERSION_MAJOR})."
        )
        return

    if not nuke.allNodes("Viewer"):
        nuke.message("Please create a viewer first.")
        return

    if nuke.activeViewer().activeInput() is None:
        nuke.message("Please connect a viewer input.")
        return

    is_panel_open = getattr(nuke, constants.NUKE_PANEL_NAME, False)
    if is_panel_open:
        panel = utils.find_window_by_title(constants.QWINDOW_TITLE)
        if panel:
            panel.close()
    else:
        setattr(nuke, constants.NUKE_PANEL_NAME, True)
        panel_instance = ChannelHub()
        constants.GC_PROTECT.append(panel_instance)
        panel_instance.show()
