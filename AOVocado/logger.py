# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Debug logging for AOVocado.

Silent by default (WARNING and above only, to the terminal). Set the
AOVOCADO_DEBUG environment variable to any non-empty value *before*
launching Nuke to enable DEBUG-level output - printed to the
terminal/Script Editor, and also written to
~/.nuke/AOVocado_debug.log so it's still available if the terminal
that launched Nuke isn't visible/accessible (e.g. launched from a
pipeline tool or desktop shortcut).

    export AOVOCADO_DEBUG=1
    nuke
"""

import logging
import os

_DEBUG_ENV_VAR = "AOVOCADO_DEBUG"
_LOG_FILE_PATH = os.path.join(
    os.path.expanduser("~"), ".nuke", "AOVocado_debug.log"
)

_debug_enabled = bool(os.environ.get(_DEBUG_ENV_VAR))

_logger = logging.getLogger("AOVocado")
_logger.setLevel(logging.DEBUG if _debug_enabled else logging.WARNING)
_logger.propagate = False

_formatter = logging.Formatter(
    "[AOVocado] %(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)
_logger.addHandler(_console_handler)

if _debug_enabled:
    _file_handler = logging.FileHandler(_LOG_FILE_PATH)
    _file_handler.setFormatter(_formatter)
    _logger.addHandler(_file_handler)
    _logger.info("Debug logging enabled - also writing to %s", _LOG_FILE_PATH)


def get_logger(name):
    """Returns an AOVocado logger for the given module.

    Args:
        name (str): The calling module's `__name__`.

    Returns:
        logging.Logger: A logger under the shared "AOVocado" hierarchy -
            active at DEBUG level if AOVOCADO_DEBUG was set in the
            environment when Nuke started, WARNING level otherwise.
    """
    return logging.getLogger(name)
