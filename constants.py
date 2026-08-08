"""Small shared constants for channelHub.

Author: Asier Aparicio
"""

# Name of the dynamic nuke.<attr> flag used to track whether the panel is
# currently open (see main.run()). Not a real Nuke preference/knob - just a
# runtime attribute set/read via getattr/setattr on the `nuke` module.
NUKE_PANEL_NAME = "channelHubPanel"

# QApplication window title, used by main.run() to find the open panel
# among QApplication.topLevelWidgets() when closing it.
QWINDOW_TITLE = "channelHub"

# Holds a strong reference to the currently-open panel instance. Without
# this, nothing else keeps the panel window alive after main.run() returns
# (Nuke doesn't hold a reference either), so Qt/Python would garbage-collect
# it and the window would vanish or crash unpredictably. main.py appends to
# this before calling panel_instance.show().
GC_PROTECT = []
