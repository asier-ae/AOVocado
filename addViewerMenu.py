import nuke

from . import config, main

SETTINGS = config.Settings()


def add_menu(menu, toolbar):

    viewer_menu = nuke.menu("Viewer")
    viewer_menu = viewer_menu.addMenu("channelHub")
    viewer_menu.addCommand("channelHub", main.run, SETTINGS.HOTKEY)
