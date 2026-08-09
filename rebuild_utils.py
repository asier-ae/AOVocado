"""Shared node-graph helpers for the Rebuild Beauty features.

Backdrop creation/sizing/z-ordering and node re-centering, used by the
subtractive rebuild (`rebuild_subtractive.py`) and meant to be reused by its
additive counterpart once that gets built.

Author: Asier Aparicio
"""

import random

import nuke

BACKDROP_TILE_COLOR = 1062692607  # Cyan
BACKDROP_APPEARANCE = "Border"
BACKDROP_BORDER_WIDTH = 25
BACKDROP_FONT_COLOR = 4294967295  # White
BACKDROP_FONT_SIZE = 40


def is_node_inside_backdrop(node, backdrop_node):
    """Checks whether a node is geometrically inside a backdrop node.

    Args:
        node (nuke.Node): The node to check.
        backdrop_node (nuke.Node): The backdrop node.

    Returns:
        bool: True if `node` is fully inside `backdrop_node`.
    """
    top_left_inside = (
        node.xpos() >= backdrop_node.xpos() and node.ypos() >= backdrop_node.ypos()
    )
    bottom_right_inside = (
        node.xpos() + node.screenWidth()
        <= backdrop_node.xpos() + backdrop_node.screenWidth()
        and node.ypos() + node.screenHeight()
        <= backdrop_node.ypos() + backdrop_node.screenHeight()
    )
    return top_left_inside and bottom_right_inside


def calculate_backdrop_z_order(selected_nodes):
    """Calculates a z_order for a new backdrop so it doesn't hide others.

    Args:
        selected_nodes (list[nuke.Node]): The nodes the backdrop will contain.

    Returns:
        int: The z_order to use for the new backdrop.
    """
    selected_backdrops = nuke.selectedNodes("BackdropNode")
    if selected_backdrops:
        return min(node.knob("z_order").value() for node in selected_backdrops) - 1

    z_order = 0
    for node in selected_nodes:
        for backdrop in nuke.allNodes("BackdropNode"):
            if is_node_inside_backdrop(node, backdrop):
                z_order = max(z_order, backdrop.knob("z_order").value() + 1)
    return z_order


def create_auto_backdrop(margin_left, margin_top, margin_right, margin_bottom):
    """Creates a backdrop sized to fit the currently selected nodes.

    Args:
        margin_left (int): Left margin, in pixels.
        margin_top (int): Top margin, in pixels.
        margin_right (int): Right margin, in pixels.
        margin_bottom (int): Bottom margin, in pixels.

    Returns:
        nuke.Node: The created backdrop node.
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return nuke.nodes.BackdropNode()

    bd_x = min(node.xpos() for node in selected_nodes) + margin_left
    bd_y = min(node.ypos() for node in selected_nodes) + margin_top
    bd_w = (
        max(node.xpos() + node.screenWidth() for node in selected_nodes)
        - min(node.xpos() for node in selected_nodes)
        + margin_right
        - margin_left
    )
    bd_h = (
        max(node.ypos() + node.screenHeight() for node in selected_nodes)
        - min(node.ypos() for node in selected_nodes)
        + margin_bottom
        - margin_top
    )

    backdrop = nuke.nodes.BackdropNode(
        xpos=bd_x,
        ypos=bd_y,
        bdwidth=bd_w,
        bdheight=bd_h,
        tile_color=int(random.random() * (16 - 10)) + 10,
        note_font_size=42,
        z_order=calculate_backdrop_z_order(selected_nodes),
    )

    backdrop["selected"].setValue(False)
    for node in selected_nodes:
        node["selected"].setValue(True)
    return backdrop


def move_nodes_to_center(nodes):
    """Offsets each node so its collective center lands on its own position.

    Args:
        nodes (list[nuke.Node]): The nodes to re-center.
    """
    for node in nodes:
        node.setXYpos(
            node.xpos() - node.screenWidth() // 2,
            node.ypos() - node.screenHeight() // 2,
        )
