"""Creates Nuke nodes from selected channels.

Two layouts: a vertical stack (each node chained onto the previous one,
relying on Nuke's default `createNode()` auto-connect behavior) and a
horizontal row (each node branching independently off one shared Dot, which
needs manual positioning/wiring since that's not what auto-connect gives you).

Author: Asier Aparicio
"""

import nuke

from . import utils


@utils.undo_block
def create_node_vertical(node_class, node_knob, channel_names):
    """Creates one node per channel, each chained below the previous one.

    Relies entirely on Nuke's default `createNode()` behavior (auto-connect
    to the current selection, auto-position below it) rather than setting
    positions explicitly - that default behavior already produces exactly
    the vertical stack this is named for, chained onto whatever node was
    selected in the graph before this was called.

    Args:
        node_class (str): The Nuke node class to create (e.g. "Shuffle2").
        node_knob (str): The knob on each created node to set with its channel name.
        channel_names (list[str]): Channel names to create one node per, in order.
    """
    created_nodes = []
    for channel in channel_names:
        node = nuke.createNode(node_class, inpanel=False)
        node[node_knob].setValue(channel)
        created_nodes.append(node)

    for node in created_nodes:
        node["selected"].setValue(True)


@utils.undo_block
def create_nodes_horizontal(node_class, node_knob, channel_names, h_sep, v_sep):
    """Creates one node per channel in a horizontal row branching off a Dot.

    Args:
        node_class (str): The Nuke node class to create (e.g. "Shuffle2").
        node_knob (str): The knob on each created node to set with its channel name.
        channel_names (list[str]): Channel names to create one node per, in order.
        h_sep (int): Horizontal pixel spacing between adjacent nodes in the row.
        v_sep (int): Vertical pixel gap between the Dot's actual bottom edge
            and the node row (not from the Dot's xpos/ypos corner).
    """
    if not channel_names:
        return

    if len(channel_names) == 1:
        # A "row" of one node doesn't need a shared branch point - skip the
        # Dot and create the node directly, same as create_node_vertical()
        # would for a single channel.
        node = nuke.createNode(node_class, inpanel=False)
        node[node_knob].setValue(channel_names[0])
        node["selected"].setValue(True)
        return

    utils.deselect_all_nodes()
    dot = nuke.createNode("Dot", inpanel=False)
    # xpos()/ypos() knobs return floats; setXYpos() requires ints.
    dot_x, dot_y = int(dot["xpos"].value()), int(dot["ypos"].value())
    dot_width, dot_height = dot.screenWidth(), dot.screenHeight()
    utils.deselect_all_nodes()

    created_nodes = [dot]
    node_ypos = dot_y + dot_height + v_sep
    node_xpos = None
    for channel in channel_names:
        node = nuke.createNode(node_class, inpanel=False)
        node[node_knob].setValue(channel)
        if node_xpos is None:
            # Center the first row node under the Dot using both real
            # widths, queried now rather than assumed - node classes vary
            # in width, so this can't be precomputed before creating one.
            node_xpos = dot_x + dot_width // 2 - node.screenWidth() // 2
        node.setXYpos(int(node_xpos), int(node_ypos))
        node.connectInput(0, dot)
        node_xpos += h_sep
        created_nodes.append(node)
        # Stops this node from being the auto-connect target of the next
        # createNode() call in the loop - each node should only connect to
        # the shared Dot, not chain onto its horizontal neighbor.
        utils.deselect_all_nodes()

    for node in created_nodes:
        node["selected"].setValue(True)
