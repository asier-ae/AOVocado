"""Registers channelHub under Nuke's Viewer menu.

This module's `add_menu()` must be called from the user's own
`~/.nuke/menu.py`, outside this repo - nothing here auto-registers on
import (this package's `__init__.py` is empty).

Author: Asier Aparicio
"""

#### NOT BEING USED RIGHT NOW
import nuke

from . import config, constants, logger, main

_log = logger.get_logger(__name__)

# Module-level singleton, read once at import time. Changing
# channelHub_global_settings.json's HOTKEY requires restarting Nuke (or
# re-importing this module) for the registered menu command below to pick it up.
SETTINGS = config.Settings()


def add_menu():
    """Adds a "channelHub" submenu with a hotkey command under Nuke's Viewer menu.

    No-ops on Nuke versions below `constants.MIN_NUKE_VERSION` - nothing to
    click into if the tool can't actually launch there anyway (see
    `main.run()`'s own guard for the interactive-launch side of this).
    """
    if nuke.NUKE_VERSION_MAJOR < constants.MIN_NUKE_VERSION:
        _log.debug(
            "skipped registering menu: Nuke %s < MIN_NUKE_VERSION %s",
            nuke.NUKE_VERSION_MAJOR,
            constants.MIN_NUKE_VERSION,
        )
        return

    viewer_menu = nuke.menu("Viewer")
    viewer_menu = viewer_menu.addMenu("channelHub")
    viewer_menu.addCommand("channelHub", main.run, SETTINGS.HOTKEY)
    _log.debug("registered Viewer menu entry with hotkey %s", SETTINGS.HOTKEY)
