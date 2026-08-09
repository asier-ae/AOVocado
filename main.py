"""Entry points for opening/closing channelHub and reacting to viewer changes.

Author: Asier Aparicio
"""

import nuke

from . import constants
from ._vendor.Qt.QtWidgets import QApplication
from .channelHub import ChannelHub


def _find_open_panel():
    """Returns the open channelHub panel widget, or None if it isn't open.

    Matches by window title (`constants.QWINDOW_TITLE`) rather than by a
    stored reference, since both callers need to find the panel from a
    context with no direct access to any particular `ChannelHub` instance:
    `run()` is a fresh call every hotkey press, and `viewer_updated()` runs
    as callback code Nuke executes in its own scope (see below).

    Returns:
        ChannelHub or None: The open panel widget, if any.
    """
    for widget in QApplication.topLevelWidgets():
        if widget.windowTitle() == constants.QWINDOW_TITLE:
            return widget
    return None


def run():
    """Opens the channelHub panel, or closes it if already open.

    Intended to be called from a Nuke menu command/hotkey. Guards on having
    a Viewer with a connected input, since ChannelManager needs a valid
    viewer input node to collect channels from.

    channelHub isn't a native Nuke panel/pane, so there's no built-in
    open/closed state to query. Instead, "is it open" is tracked via a
    dynamic `nuke.<NUKE_PANEL_NAME>` attribute, and closing is done via
    `_find_open_panel()` - there's no persistent Python reference to the
    panel between separate hotkey presses without this, since each press is
    a fresh call to this function.
    """
    if not nuke.allNodes("Viewer"):
        nuke.message("Please create a viewer first.")
        return

    if nuke.activeViewer().activeInput() is None:
        nuke.message("Please connect a viewer input.")
        return

    is_panel_open = getattr(nuke, constants.NUKE_PANEL_NAME, False)
    if is_panel_open:
        panel = _find_open_panel()
        if panel:
            panel.close()
    else:
        setattr(nuke, constants.NUKE_PANEL_NAME, True)
        panel_instance = ChannelHub()
        constants.GC_PROTECT.append(panel_instance)
        panel_instance.show()


def viewer_updated():
    """Reloads the open panel's channel lists when the viewer's input changes.

    Set as a `knobChanged` callback on the active viewer by `ChannelHub`'s
    `_setup_viewer_callback()` (via `models.ViewerManager.add_callback()`).
    Nuke executes this in the viewer node's own callback context
    (`nuke.thisNode()`/`nuke.thisKnob()`) - only "inputChange"/"input_number"
    knob changes (the viewer's connected input actually changing) should
    trigger a reload; everything else is a no-op.
    """
    viewer = nuke.thisNode()
    try:
        # Guards against a stale/detached node context - can happen if this
        # fires while Nuke is mid-teardown of the viewer node.
        viewer.name()
    except Exception:
        return

    knob = nuke.thisKnob()
    if not knob or knob.name() not in ("inputChange", "input_number"):
        return

    panel = _find_open_panel()
    if panel:
        panel.reload_channels()
