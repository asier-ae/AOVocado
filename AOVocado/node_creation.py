# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Creates Nuke nodes from selected channels.

Two layouts: a vertical stack (each node connected to the previous one via
Nuke's own auto-connect, with Y position explicitly offset from the
previous node - see `create_node_vertical()` for why) and a horizontal row
(each node branching independently off one shared Dot, which needs manual
positioning/wiring since that's not what auto-connect gives you).

Each node can come from either a registered node class (`SOURCE_CLASS`,
e.g. "Shuffle2") or a standalone toolset/group `.nk` file loaded via
`nuke.loadToolset()` (`SOURCE_TOOLSET`) - see `utils.validate_toolset_path()`
for the constraint a toolset file must satisfy. `loadToolset()` has the
same auto-connect-to-selection/auto-position/auto-reselect behavior as
`createNode()` (confirmed empirically - it isn't documented), so toolset
nodes need no more manual positioning than class-based ones do.
"""

import nuke

from . import logger, utils

_log = logger.get_logger(__name__)

# Must match preferencesUI.ui's BUTTON{1..4}_SOURCE combo item text exactly
# - that text is what gets saved/read as the source value.
SOURCE_CLASS = "Node class"
SOURCE_TOOLSET = "Nuke script path"

# Vertical gap between the Dot's actual bottom edge and its row of nodes in
# create_nodes_horizontal(). Fixed rather than user-configurable - this
# spacing has never needed to be tunable independently of node-to-node
# spacing (cfg_main_v_sep, used by create_node_vertical() instead).
_HORIZONTAL_DOT_V_SEP = 100


def _load_toolset_node(path, node_knob, channel_name):
    """Loads a toolset/group file and configures the resulting node.

    No manual deselect/reselect around `nuke.loadToolset()` - confirmed by
    testing in Nuke that it already deselects everything and selects just
    the node it created, whether or not anything was selected going in
    (and, if something was, connects/positions the new node below it,
    same as `nuke.createNode()`'s own auto-connect).

    Args:
        path (str): Path to the .nk file to load.
        node_knob (str): The knob on the resulting node to set with the channel name.
        channel_name (str): The channel name to set on `node_knob`.

    Returns:
        nuke.Node: The single node the toolset created.

    Raises:
        ValueError: If the file didn't create exactly one top-level node
            - a defensive re-check, since `utils.validate_toolset_path()`
            should already have caught this before this is ever called.
    """
    nuke.loadToolset(path)
    pasted_nodes = nuke.selectedNodes()
    if len(pasted_nodes) != 1:
        raise ValueError(
            f"Toolset created {len(pasted_nodes)} top-level nodes (expected 1): {path}"
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
        return _load_toolset_node(node_class_or_path, node_knob, channel_name)
    node = nuke.createNode(node_class_or_path, inpanel=False)
    node[node_knob].setValue(channel_name)
    return node


@utils.undo_block
def create_node_vertical(
    node_class, node_knob, channel_names, source=SOURCE_CLASS, v_sep=0
):
    """Creates one node per channel, each positioned below the previous one.

    Connection still comes entirely from Nuke's own auto-connect
    (`nuke.createNode()` for SOURCE_CLASS, `nuke.loadToolset()` for
    SOURCE_TOOLSET - both chain onto whatever's selected the same way) -
    that part was never the problem. Y position is explicitly overridden
    for every node after the first, as a flat offset from the previous
    node's own Y, via `setXYpos()` - **not** `node["ypos"].setValue()`.
    This matters: a node that just got auto-connected to a prior selection
    has its position finalized by Nuke on some later idle/redraw pass, not
    immediately - setting the `ypos` knob directly changes what
    `.value()` reports right away, but doesn't stop that later pass from
    silently overwriting it back to Nuke's own auto-connect position
    moments afterward. `setXYpos()` is the same API Nuke's own UI uses
    when a node is dragged, and calling it is what actually cancels that
    pending auto-position finalization - confirmed by testing directly in
    Nuke (a Script Editor snippet showed `ypos` reporting the overridden
    value immediately after `setValue()`, then reverting on a second read
    moments later with nothing else run in between). X position is passed
    through unchanged (read from `previous_node`, not touched otherwise) -
    `setXYpos()` needs both, but only Y is meant to change here.

    Args:
        node_class (str): The Nuke node class to create (SOURCE_CLASS) or
            the toolset .nk path to load (SOURCE_TOOLSET).
        node_knob (str): The knob on each created node to set with its channel name.
        channel_names (list[str]): Channel names to create one node per, in order.
        source (str, optional): SOURCE_CLASS or SOURCE_TOOLSET. Defaults to
            SOURCE_CLASS.
        v_sep (int, optional): Vertical pixel gap from one node's Y
            position to the next's. Defaults to 0.
    """
    _log.debug(
        "create_node_vertical: source=%s class=%s channels=%s",
        source,
        node_class,
        len(channel_names),
    )
    created_nodes = []
    previous_node = None
    for channel in channel_names:
        node = _create_one_node(source, node_class, node_knob, channel)
        if previous_node is not None:
            prev_y = int(previous_node["ypos"].value())
            node.setXYpos(int(previous_node.xpos()), int(prev_y + v_sep))
        previous_node = node
        created_nodes.append(node)

    for node in created_nodes:
        node["selected"].setValue(True)


@utils.undo_block
def create_nodes_horizontal(
    node_class, node_knob, channel_names, h_sep, source=SOURCE_CLASS
):
    """Creates one node per channel in a horizontal row branching off a Dot.

    Args:
        node_class (str): The Nuke node class to create (SOURCE_CLASS) or
            the toolset .nk path to paste (SOURCE_TOOLSET).
        node_knob (str): The knob on each created node to set with its channel name.
        channel_names (list[str]): Channel names to create one node per, in order.
        h_sep (int): Horizontal pixel spacing between adjacent nodes in the row.
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
    node_ypos = dot_y + dot_height + _HORIZONTAL_DOT_V_SEP
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
