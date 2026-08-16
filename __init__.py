# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""AOVocado - a Nuke panel for browsing/categorizing/viewing render
channels/AOVs in the Viewer.

Registers itself under Nuke's built-in Edit menu (with its configured
hotkey) as soon as this package is imported, if running inside Nuke's GUI
on a supported version - add `import AOVocado` to your own
`~/.nuke/menu.py`, no further setup call needed.
"""

import nuke

from . import config, constants, logger

_log = logger.get_logger(__name__)
_log.debug("AOVocado package import started")

if nuke.env.get("gui") and nuke.NUKE_VERSION_MAJOR >= constants.MIN_NUKE_VERSION:
    from . import main

    _log.debug("registering AOVocado menu now")
    _settings = config.Settings()
    # addCommand's name can be a slash-separated path - Nuke builds any
    # missing intermediate submenus automatically, reusing "Edit" (an
    # existing built-in menu) rather than us creating a new top-level one.
    nuke.menu("Nuke").addCommand(
        "Edit/AOVocado/Open AOVocado", main.run, _settings.HOTKEY
    )
    print(_settings.get_copyright_line())
