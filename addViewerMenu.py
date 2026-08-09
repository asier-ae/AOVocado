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


def add_menu():
    """Adds a "channelHub" submenu with a hotkey command under Nuke's Viewer menu."""
    viewer_menu = nuke.menu("Viewer")
    viewer_menu = viewer_menu.addMenu("channelHub")
    viewer_menu.addCommand("channelHub", main.run, SETTINGS.HOTKEY)
