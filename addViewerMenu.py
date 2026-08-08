"""Registers channelHub under Nuke's Viewer menu.

This module's `add_menu()` must be called from the user's own
`~/.nuke/menu.py`, outside this repo - nothing here auto-registers on
import (this package's `__init__.py` is empty).

Author: Asier Aparicio
"""

import nuke

from . import config, main

# Module-level singleton, read once at import time. Changing
# global_settings.json's HOTKEY requires restarting Nuke (or re-importing
# this module) for the registered menu command below to pick it up.
SETTINGS = config.Settings()


def add_menu(menu, toolbar):
    """Adds a "channelHub" submenu with a hotkey command under Nuke's Viewer menu.

    Args:
        menu: Unused - kept for a consistent call signature with other
            menu-registration hooks. The Viewer menu is looked up directly
            via nuke.menu("Viewer") instead.
        toolbar: Unused, same reason as `menu`.
    """
    viewer_menu = nuke.menu("Viewer")
    viewer_menu = viewer_menu.addMenu("channelHub")
    viewer_menu.addCommand("channelHub", main.run, SETTINGS.HOTKEY)
