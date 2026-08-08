import nuke
from PySide6.QtWidgets import QApplication

from . import constants
from .channelHub import ChannelHub


def run():

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
