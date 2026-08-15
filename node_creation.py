"""Creates Nuke nodes from selected channels.

Two layouts: a vertical stack (each node chained onto the previous one,
relying on Nuke's default `createNode()` auto-connect behavior) and a
horizontal row (each node branching independently off one shared Dot, which
needs manual positioning/wiring since that's not what auto-connect gives you).

Each node can come from either a registered node class (`SOURCE_CLASS`,
e.g. "Shuffle2") or a standalone toolset/group `.nk` file pasted in via
`nuke.nodePaste()` (`SOURCE_TOOLSET`) - see `utils.validate_toolset_path()`
for the constraint a toolset file must satisfy.

Author: Asier Aparicio
"""

import nuke

from . import logger, utils

_log = logger.get_logger(__name__)

# Must match preferencesUI.ui's BUTTON{1..4}_SOURCE combo item text exactly
# - that text is what gets saved/read as the source value.
SOURCE_CLASS = "Node class"
SOURCE_TOOLSET = "Nuke script path"


def _paste_toolset_node(path, node_knob, channel_name):
    """Pastes a toolset/group file and configures the resulting node.

    Args:
        path (str): Path to the .nk file to paste.
        node_knob (str): The knob on the pasted node to set with the channel name.
        channel_name (str): The channel name to set on `node_knob`.

    Returns:
        nuke.Node: The single node the toolset pasted in.

    Raises:
        ValueError: If the file didn't paste in exactly one top-level node
            - a defensive re-check, since `utils.validate_toolset_path()`
            should already have caught this before this is ever called.
    """
    utils.deselect_all_nodes()
    nuke.nodePaste(path)
    pasted_nodes = nuke.selectedNodes()
    if len(pasted_nodes) != 1:
        raise ValueError(
            f"Toolset pasted {len(pasted_nodes)} top-level nodes (expected 1): {path}"
        )
    node = pasted_nodes[0]
    node[node_knob].setValue(channel_name)
    return node


def _create_one_node(source, node_class_or_path, node_knob, channel_name):
    """Creates and configures a single node from either source.

    Args:
        source (str): SOURCE_CLASS or SOURCE_TOOLSET.
        node_class_or_path (str): A node class name (SOURCE_CLASS) or a
            path to a toolset .nk file (SOURCE_TOOLSET).
        node_knob (str): The knob on the created node to set with the channel name.
        channel_name (str): The channel name to set on `node_knob`.

    Returns:
        nuke.Node: The created/pasted node.
    """
    if source == SOURCE_TOOLSET:
        return _paste_toolset_node(node_class_or_path, node_knob, channel_name)
    node = nuke.createNode(node_class_or_path, inpanel=False)
    node[node_knob].setValue(channel_name)
    return node


@utils.undo_block
def create_node_vertical(
    node_class, node_knob, channel_names, source=SOURCE_CLASS, v_sep=None
):
    """Creates one node per channel, each chained below the previous one.

    For SOURCE_CLASS, relies entirely on Nuke's default `createNode()`
    behavior (auto-connect to the current selection, auto-position below
    it) rather than setting positions explicitly - that default behavior
    already produces exactly the vertical stack this is named for, chained
    onto whatever node was selected in the graph before this was called.

    For SOURCE_TOOLSET, `nuke.nodePaste()` doesn't have that same
    auto-connect/auto-position behavior, so each pasted node is explicitly
    connected to and positioned below the previous one instead (starting
    from whatever was selected before this was called, if exactly one node
    was) - manual chaining, mirroring the pattern `create_nodes_horizontal()`
    already uses for its Dot-branch children.

    Args:
        node_class (str): The Nuke node class to create (SOURCE_CLASS) or
            the toolset .nk path to paste (SOURCE_TOOLSET).
        node_knob (str): The knob on each created node to set with its channel name.
        channel_names (list[str]): Channel names to create one node per, in order.
        source (str, optional): SOURCE_CLASS or SOURCE_TOOLSET. Defaults to
            SOURCE_CLASS.
        v_sep (int, optional): Vertical pixel gap between chained toolset
            nodes. Only used for SOURCE_TOOLSET.
    """
    _log.debug(
        "create_node_vertical: source=%s class=%s channels=%s",
        source,
        node_class,
        len(channel_names),
    )
    created_nodes = []

    if source == SOURCE_TOOLSET:
        anchor_nodes = nuke.selectedNodes()
        anchor = anchor_nodes[0] if len(anchor_nodes) == 1 else None
        for channel in channel_names:
            node = _paste_toolset_node(node_class, node_knob, channel)
            if anchor is not None:
                anchor_x, anchor_y = int(anchor["xpos"].value()), int(anchor["ypos"].value())
                node_x = anchor_x + anchor.screenWidth() // 2 - node.screenWidth() // 2
                node_y = anchor_y + anchor.screenHeight() + v_sep
                node.setXYpos(node_x, node_y)
                node.connectInput(0, anchor)
            anchor = node
            created_nodes.append(node)
    else:
        for channel in channel_names:
            node = nuke.createNode(node_class, inpanel=False)
            node[node_knob].setValue(channel)
            created_nodes.append(node)

    for node in created_nodes:
        node["selected"].setValue(True)


@utils.undo_block
def create_nodes_horizontal(
    node_class, node_knob, channel_names, h_sep, v_sep, source=SOURCE_CLASS
):
    """Creates one node per channel in a horizontal row branching off a Dot.

    Args:
        node_class (str): The Nuke node class to create (SOURCE_CLASS) or
            the toolset .nk path to paste (SOURCE_TOOLSET).
        node_knob (str): The knob on each created node to set with its channel name.
        channel_names (list[str]): Channel names to create one node per, in order.
        h_sep (int): Horizontal pixel spacing between adjacent nodes in the row.
        v_sep (int): Vertical pixel gap between the Dot's actual bottom edge
            and the node row (not from the Dot's xpos/ypos corner).
        source (str, optional): SOURCE_CLASS or SOURCE_TOOLSET. Defaults to
            SOURCE_CLASS. Only the node-creation step itself differs -
            positioning/wiring below already applies to either source.
    """
    _log.debug(
        "create_nodes_horizontal: source=%s class=%s channels=%s",
        source,
        node_class,
        len(channel_names),
    )
    if not channel_names:
        return

    if len(channel_names) == 1:
        # A "row" of one node doesn't need a shared branch point - skip the
        # Dot and create the node directly, same as create_node_vertical()
        # would for a single channel.
        node = _create_one_node(source, node_class, node_knob, channel_names[0])
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
        node = _create_one_node(source, node_class, node_knob, channel)
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
