# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""Samples pixel values from every channel at the viewer's mouse position.

The math in `_get_sample_position()` and `_get_effective_image_dimensions()`
converts the viewer's normalized sample-bbox coordinates into absolute
pixel coordinates, correctly accounting for proxy mode, viewer downrez,
and anamorphic pixel aspect ratio.
"""

import logging

import nuke

from . import logger
from .viewer import ViewerManager

_log = logger.get_logger(__name__)


def sample_viewer_channels(threshold=0.005, channel_manager=None):
    """Samples all channels at the viewer's current mouse position.

    Finds the active viewer input, calculates the correct sampling
    coordinates considering proxy and down-rez settings, samples all
    available channels, and returns those that exceed a given threshold.

    Args:
        threshold (float, optional): The minimum pixel value for a channel
            to be considered active. Defaults to 0.005.
        channel_manager (channels.ChannelManager, optional): If given,
            channels it reports as excluded (`is_channel_excluded()`) are
            skipped entirely - never sampled, never returned. Defaults to
            None (no exclusion).

    Returns:
        list[tuple]: A list of (channel_name, value) tuples for channels
            exceeding the threshold, sorted by value in descending order.
            Returns an empty list if sampling fails.
    """
    try:
        input_node = ViewerManager.get_viewer_input_node()
        if not input_node:
            return []

        sample_position = _get_sample_position(input_node)
        if sample_position is None:
            return []

        if _log.isEnabledFor(logging.DEBUG):
            img_width, img_height = _get_effective_image_dimensions(input_node)
            viewer_node = nuke.activeViewer().node()
            _log.debug(
                "input=%s position=%s image_dims=%s downrez=%s proxy=%s/%s pixel_aspect=%s",
                input_node.name(),
                tuple(round(p, 2) for p in sample_position),
                (img_width, img_height),
                viewer_node["downrez"].value(),
                nuke.root()["proxy"].value(),
                nuke.root()["proxy_scale"].value(),
                input_node.format().pixelAspect(),
            )

        detected_channels = _sample_channels_at_position(
            input_node, sample_position, threshold, channel_manager
        )
        _log.debug("threshold=%s detected_channels=%s", threshold, detected_channels)

        return _sort_channels_by_value(detected_channels)

    except Exception:
        _log.exception("sample_viewer_channels failed")
        return []


def _get_active_viewer_and_node():
    """Gets the active viewer window and its corresponding node.

    Returns:
        tuple: A tuple containing the active viewer window and the viewer
            node, or (None, None) if not found.
    """
    viewer = nuke.activeViewer()
    if not viewer:
        return None, None

    view_node = viewer.node()
    return viewer, view_node


def _get_sample_position(input_node):
    """Calculates the pixel coordinates to sample based on mouse position.

    The viewer provides normalized coordinates, which this function converts
    to absolute pixel coordinates, accounting for image aspect ratio.

    Args:
        input_node (nuke.Node): The node being viewed, used to get dimensions.

    Returns:
        tuple or None: A tuple (x, y) of the pixel coordinates, or None.
    """
    viewer, view_node = _get_active_viewer_and_node()
    if not viewer or not view_node:
        return None

    bbox_info = view_node["colour_sample_bbox"].value()

    # Get image dimensions accounting for proxy mode
    img_width, img_height = _get_effective_image_dimensions(input_node)

    # Account for non-square (anamorphic) pixels: the viewer's normalized
    # coordinates are based on the image's displayed (square-pixel) aspect
    # ratio, not its raw resolution ratio, so pixelAspect must be folded in.
    pixel_aspect = input_node.format().pixelAspect()
    aspect = (img_width * pixel_aspect) / img_height

    # Convert normalized viewer coordinates to pixel coordinates
    x_pos = (bbox_info[0] * 0.5 + 0.5) * img_width
    y_pos = (((bbox_info[1] * 0.5) + (0.5 / aspect)) * aspect) * img_height

    return (x_pos, y_pos)


def _get_effective_image_dimensions(input_node):
    """Gets image dimensions, scaled by proxy and down-rez settings.

    Args:
        input_node (nuke.Node): The node to get dimensions from.

    Returns:
        tuple: A tuple (width, height) of the effective dimensions.
    """
    img_width = float(input_node.width())
    img_height = float(input_node.height())

    proxy_scale = 1
    downrez_scale = 1

    # Apply proxy scaling if enabled
    proxy_enabled = nuke.root()["proxy"].value()
    if proxy_enabled:
        proxy_scale = nuke.root()["proxy_scale"].value()

    viewer_node = nuke.activeViewer().node()
    downrez_scale = viewer_node["downrez"].value()
    img_width = img_width * proxy_scale * (1 / int(downrez_scale))
    img_height = img_height * proxy_scale * (1 / int(downrez_scale))

    return img_width, img_height


def _sample_channels_at_position(input_node, position, threshold, channel_manager=None):
    """Samples all channels at a specific pixel and filters by a threshold.

    Args:
        input_node (nuke.Node): The node to sample from.
        position (tuple): The (x, y) pixel coordinates to sample.
        threshold (float): The minimum value for a channel to be kept.
        channel_manager (channels.ChannelManager, optional): If given,
            excluded channels (`is_channel_excluded()`) are skipped before
            `input_node.sample()` is called on them - that call is the
            expensive part of this loop, so excluded channels never pay
            for it. Defaults to None (no exclusion).

    Returns:
        dict: A dictionary of {channel_layer: max_value} for all channels
            exceeding the threshold.
    """
    x_pos, y_pos = position
    detected_channels = {}
    all_channels = input_node.channels()

    for channel_name in all_channels:
        base_name = channel_name.split(".")[0]
        if channel_manager and channel_manager.is_channel_excluded(base_name):
            continue

        try:
            pixel_value = input_node.sample(channel_name, x_pos, y_pos)

            if pixel_value > threshold:
                # Keep only the highest value for each channel layer
                if (
                    base_name not in detected_channels
                    or pixel_value > detected_channels[base_name]
                ):
                    detected_channels[base_name] = pixel_value

        except RuntimeError:
            continue

    return detected_channels


def _sort_channels_by_value(channels_dict):
    """Sorts a dictionary of channels by their values in descending order.

    Args:
        channels_dict (dict): A dictionary of {channel: value}.

    Returns:
        list[tuple]: A list of (channel, value) tuples, sorted by value.
    """
    return sorted(channels_dict.items(), key=lambda item: item[1], reverse=True)
