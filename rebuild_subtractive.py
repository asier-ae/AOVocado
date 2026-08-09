"""Builds a subtractive layer-reconstruction node network.

For each given channel, subtracts it from the beauty pass and shuffles it
back out as its own explicit output layer, wrapping each channel's group of
nodes in a styled backdrop.

Author: Asier Aparicio
"""

from dataclasses import dataclass

import nuke

from . import rebuild_utils, utils

LAYOUT_RIGHT = "Right"
LAYOUT_LEFT = "Left"
OPERATION_FROM = "from"
OPERATION_PLUS = "plus"
OUTPUT_RGB = "rgb"
INPUT_RGBA = "rgba"
FROM_INPUT_VALUE = "{1} B A"


@dataclass
class SubtractiveLayoutConfig:
    """Layout/spacing settings for one subtractive-rebuild run.

    Attributes:
        h_sep (int): Horizontal separation between a channel group and its
            shuffle branch.
        v_sep_base (int): Base vertical separation between adjacent nodes.
        v_sep_grade (int): Vertical separation around the merge/shuffle
            stage.
        bd_sep_left (int): Left margin for the backdrop.
        bd_sep_top (int): Top margin for the backdrop.
        bd_sep_right (int): Right margin for the backdrop.
        bd_sep_bottom (int): Bottom margin for the backdrop.
        layout_multiplier (int): -1 for a left-growing layout, 1 for right.
    """

    h_sep: int
    v_sep_base: int
    v_sep_grade: int
    bd_sep_left: int
    bd_sep_top: int
    bd_sep_right: int
    bd_sep_bottom: int
    layout_multiplier: int

    @classmethod
    def from_user_settings(cls, user_settings):
        """Builds a config from the cfg_rs_* block of user_settings.

        Settings store base units and get scaled x10 into actual pixel
        spacing here - this matches the old tool's tuned defaults (e.g.
        cfg_rs_spb_h_sep_main: 30 -> 300px); dropping the multiplier would
        leave the rebuilt network extremely cramped.

        Args:
            user_settings (dict): `settings.my_settings["user_settings"]`.

        Returns:
            SubtractiveLayoutConfig
        """
        get_setting = lambda key, default: user_settings.get(key, default) * 10

        layout_direction = user_settings.get("cfg_rs_cb_rebuild_layout", LAYOUT_RIGHT)
        layout_multiplier = -1 if layout_direction == LAYOUT_LEFT else 1

        return cls(
            h_sep=get_setting("cfg_rs_spb_h_sep_main", 30),
            v_sep_base=get_setting("cfg_rs_spb_v_sep_base", 5),
            v_sep_grade=get_setting("cfg_rs_spb_v_sep_grade", 40),
            bd_sep_left=get_setting("cfg_rs_spb_bd_sep_left", 30),
            bd_sep_top=get_setting("cfg_rs_spb_bd_sep_top", 30),
            bd_sep_right=get_setting("cfg_rs_spb_bd_sep_right", 30),
            bd_sep_bottom=get_setting("cfg_rs_spb_bd_sep_bottom", 30),
            layout_multiplier=layout_multiplier,
        )


def _style_backdrop(backdrop_node, label):
    """Applies consistent styling to a backdrop node.

    Args:
        backdrop_node (nuke.Node): The backdrop node to style.
        label (str): The label to show on the backdrop.
    """
    backdrop_node["label"].setValue(label)
    backdrop_node["tile_color"].setValue(rebuild_utils.BACKDROP_TILE_COLOR)
    backdrop_node["appearance"].setValue(rebuild_utils.BACKDROP_APPEARANCE)
    backdrop_node["border_width"].setValue(rebuild_utils.BACKDROP_BORDER_WIDTH)
    backdrop_node["note_font_color"].setValue(rebuild_utils.BACKDROP_FONT_COLOR)
    backdrop_node["note_font_size"].setValue(rebuild_utils.BACKDROP_FONT_SIZE)


# --- Node network ---


def _create_channel_nodes(channel, start_node, pos_x, pos_y, config):
    """Creates the subtract-and-reshuffle node network for one channel.

    Args:
        channel (str): The channel to subtract and shuffle back out.
        start_node (nuke.Node): The upstream node to branch off of.
        pos_x (int): X position for the group.
        pos_y (int): Y position for the group.
        config (SubtractiveLayoutConfig): Layout/spacing settings.

    Returns:
        tuple[list[nuke.Node], nuke.Node]: The created nodes, and the
            group's final output node.
    """
    side_branch_x = pos_x + (config.h_sep * config.layout_multiplier)

    dot1 = nuke.nodes.Dot(inputs=[start_node], xpos=side_branch_x, ypos=pos_y)

    shuffle_node = nuke.nodes.Shuffle2(
        in1=channel,
        label=channel,
        inputs=[dot1],
        xpos=dot1.xpos(),
        ypos=dot1.ypos() + config.v_sep_base,
    )

    merge_node = nuke.nodes.Merge2(
        operation=OPERATION_FROM,
        output=OUTPUT_RGB,
        inputs=[start_node, shuffle_node],
        xpos=pos_x,
        ypos=pos_y + config.v_sep_base,
    )

    dot2 = nuke.nodes.Dot(
        inputs=[shuffle_node],
        xpos=dot1.xpos(),
        ypos=merge_node.ypos() + config.v_sep_grade,
    )

    merge_node2 = nuke.nodes.Merge2(
        operation=OPERATION_PLUS,
        output=OUTPUT_RGB,
        inputs=[merge_node, dot2],
        xpos=merge_node.xpos(),
        ypos=merge_node.ypos() + config.v_sep_grade,
    )

    dot3 = nuke.nodes.Dot(
        inputs=[dot2], xpos=dot2.xpos(), ypos=dot2.ypos() + config.v_sep_base
    )

    shuffle_node2 = nuke.nodes.Shuffle2(
        in1=INPUT_RGBA,
        out1=channel,
        inputs=[merge_node2, dot3],
        xpos=merge_node2.xpos(),
        ypos=merge_node2.ypos() + config.v_sep_base,
    )
    shuffle_node2["fromInput1"].setValue(FROM_INPUT_VALUE)

    created_nodes = [dot1, shuffle_node, merge_node, dot2, merge_node2, dot3, shuffle_node2]
    return created_nodes, shuffle_node2


@utils.undo_block
def create_subtractive_rebuild(channels, user_settings):
    """Builds a subtractive rebuild network for the given channels.

    For each channel, builds a subtract-and-reshuffle node group chained
    below the previous channel's group, each wrapped in its own styled
    backdrop.

    Args:
        channels (list[str]): Channel names to build a network for, in order.
        user_settings (dict): `settings.my_settings["user_settings"]`,
            supplying the `cfg_rs_*` layout/spacing values.
    """
    config = SubtractiveLayoutConfig.from_user_settings(user_settings)
    all_created_nodes = []

    pos_x = int(nuke.center()[0])
    pos_y = int(nuke.center()[1])
    previous_output_node = None

    for channel in channels:
        utils.deselect_all_nodes()

        dot0 = nuke.nodes.Dot(xpos=pos_x, ypos=pos_y)
        if previous_output_node:
            dot0.setInput(0, previous_output_node)

        channel_nodes, last_node = _create_channel_nodes(
            channel, dot0, pos_x, pos_y, config
        )

        nodes_in_group = [dot0] + channel_nodes
        rebuild_utils.move_nodes_to_center(nodes_in_group)

        for node in nodes_in_group:
            node["selected"].setValue(True)

        backdrop = rebuild_utils.create_auto_backdrop(
            margin_left=-config.bd_sep_left,
            margin_top=-config.bd_sep_top,
            margin_right=config.bd_sep_right,
            margin_bottom=config.bd_sep_bottom,
        )
        _style_backdrop(backdrop, channel)
        backdrop["selected"].setValue(True)

        nodes_in_group.append(backdrop)
        all_created_nodes.extend(nodes_in_group)

        pos_y = int(
            last_node.ypos()
            + last_node.screenHeight()
            + config.bd_sep_bottom
            + 100  # Extra static padding between channel groups
            + config.bd_sep_top
        )
        previous_output_node = last_node

    for node in all_created_nodes:
        node["selected"].setValue(True)
