"""channelHub - a Nuke panel for browsing/categorizing/viewing render
channels/AOVs in the Viewer.

Registers itself under a new top-level "channelHub" Nuke menu (with its
configured hotkey) as soon as this package is imported, if running inside
Nuke's GUI on a supported version - add `import channelHub` to your own
`~/.nuke/menu.py`, no further setup call needed.

Author: Asier Aparicio
"""

import nuke

from . import config, constants, logger

_log = logger.get_logger(__name__)
_log.debug("channelHub package import started")

if nuke.env.get("gui") and nuke.NUKE_VERSION_MAJOR >= constants.MIN_NUKE_VERSION:
    from . import main

    _log.debug("registering channelHub menu now")
    _settings = config.Settings()
    # nuke.menu("channelHub") would only look up an *existing* top-level
    # menu by that name (returning None if it doesn't exist yet) - to
    # actually create a new one, it has to be added as a submenu of the
    # main menu bar, nuke.menu("Nuke").
    _channelhub_menu = nuke.menu("Nuke").addMenu("channelHub")
    _channelhub_menu.addCommand("Open ChannelHub", main.run, _settings.HOTKEY)
