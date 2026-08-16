# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Entry point for opening/closing the AOVocado panel.
"""

import nuke

from . import constants, logger, utils
from .AOVocado import AOVocado

_log = logger.get_logger(__name__)


def run():
    """Opens the AOVocado panel, or closes it if already open.

    Intended to be called from a Nuke menu command/hotkey. Guards on having
    a Viewer with a connected input, since ChannelManager needs a valid
    viewer input node to collect channels from.

    AOVocado isn't a native Nuke panel/pane, so there's no built-in
    open/closed state to query. Instead, "is it open" is tracked via a
    dynamic `nuke.<NUKE_PANEL_NAME>` attribute, and closing is done via
    `utils.find_window_by_title()` - there's no persistent Python reference
    to the panel between separate hotkey presses without this, since each
    press is a fresh call to this function.
    """
    _log.debug("run() called")

    if nuke.NUKE_VERSION_MAJOR < constants.MIN_NUKE_VERSION:
        _log.debug(
            "blocked: Nuke %s < MIN_NUKE_VERSION %s",
            nuke.NUKE_VERSION_MAJOR,
            constants.MIN_NUKE_VERSION,
        )
        nuke.message(
            f"AOVocado requires Nuke {constants.MIN_NUKE_VERSION}+ "
            f"(this is Nuke {nuke.NUKE_VERSION_MAJOR})."
        )
        return

    if not nuke.allNodes("Viewer"):
        _log.debug("blocked: no Viewer node in the script")
        nuke.message("Please create a viewer first.")
        return

    if nuke.activeViewer().activeInput() is None:
        _log.debug("blocked: active viewer has no connected input")
        nuke.message("Please connect a viewer input.")
        return

    is_panel_open = getattr(nuke, constants.NUKE_PANEL_NAME, False)
    if is_panel_open:
        _log.debug("panel already open - closing")
        panel = utils.find_window_by_title(constants.QWINDOW_TITLE)
        if panel:
            panel.close()
    else:
        _log.debug("panel not open - creating")
        setattr(nuke, constants.NUKE_PANEL_NAME, True)
        panel_instance = AOVocado()
        constants.GC_PROTECT.append(panel_instance)
        panel_instance.show()
