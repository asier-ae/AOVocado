"""Channel data models and categorization logic for channelHub.

Contains the plain data container for categorized channels
(`ChannelGroups`) and the logic that collects and categorizes viewer
channels into it (`ChannelManager`).

Author: Asier Aparicio
"""

from .viewer import ViewerManager


class ChannelGroups:
    """A plain container for the 4 categorized channel-name groups.

    Attributes:
        group_ch1 (list[str]): Channels matching group 1 (exact name match).
        group_ch2 (list[str]): Channels matching group 2 (prefix match).
        group_ch3 (list[str]): Channels matching group 3 (exact name match).
        group_ch4 (list[str]): Everything else - the catch-all group.
    """

    def __init__(self):
        """Initializes all 4 groups as empty lists."""

        self.group_ch1 = []
        self.group_ch2 = []
        self.group_ch3 = []
        self.group_ch4 = []


class ChannelManager:
    """Collects channels from the viewer and categorizes them into groups.

    Matching rules come from `channelHub_global_settings.json` via `Settings`: groups 1
    and 3 match by exact channel name (case-insensitive), group 2 matches by
    prefix (case-sensitive - see the comment on group2_prefixes below), and
    group 4 is whatever doesn't match any of the above.
    """

    def __init__(self, settings):
        """Initializes the ChannelManager with application settings.

        Args:
            settings (Settings): The application settings object.
        """
        self.settings = settings
        self.group1_set = {x.lower() for x in self.settings.GROUP1_SEARCH}
        # Prefixes need to be a tuple for .startswith(). Intentionally
        # case-sensitive, unlike groups 1/3 - group 2 prefixes are matched
        # exactly as authored in channelHub_global_settings.json.
        self.group2_prefixes = tuple(self.settings.GROUP2_SEARCH)
        self.group3_set = {x.lower() for x in self.settings.GROUP3_SEARCH}

    def categorize_channels(self, channel_list):
        """Categorizes a list of channels into predefined groups.

        The if/elif chain order below *is* the matching priority: group 1
        exact match, then group 3 exact match, then group 2 prefix match,
        else group 4. A channel that happens to satisfy more than one rule
        takes the first match, not the "best" one.

        Args:
            channel_list (list[str]): A list of full channel names (e.g., 'rgba.red').

        Returns:
            ChannelGroups: An object containing categorized lists of channel layers.
        """
        groups = ChannelGroups()

        # Extract unique channel names (before the dot)
        unique_channels = sorted(
            set(c.split(".")[0] for c in channel_list), key=lambda v: v.upper()
        )

        # Categorize channels based on configuration
        for channel in unique_channels:
            channel_lower = channel.lower()

            if channel_lower in self.group1_set:
                groups.group_ch1.append(channel)
            elif channel_lower in self.group3_set:
                groups.group_ch3.append(channel)
            # .startswith can accept a tuple of prefixes
            elif channel.startswith(self.group2_prefixes):
                groups.group_ch2.append(channel)
            else:
                groups.group_ch4.append(channel)

        return groups

    def collect_channels_from_viewer(self):
        """Collects and categorizes channels from the active viewer's input.

        Returns:
            ChannelGroups: An object containing the categorized channels.
            Always a valid (possibly empty) instance, never None - callers
            rely on this and iterate its 4 lists unconditionally.
        """
        viewer_input_node = ViewerManager.get_viewer_input_node()
        if not viewer_input_node:
            return ChannelGroups()

        all_channels = viewer_input_node.channels()
        return self.categorize_channels(all_channels)
