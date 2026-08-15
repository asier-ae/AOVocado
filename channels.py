"""Channel data models and categorization logic for AOVocado.

Contains the plain data container for categorized channels
(`ChannelGroups`) and the logic that collects and categorizes viewer
channels into it (`ChannelManager`).

Author: Asier Aparicio
"""

from . import logger
from .viewer import ViewerManager

_log = logger.get_logger(__name__)


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

    Matching rules come from `AOVocado_global_settings.json` via `Settings`: groups 1
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
        # exactly as authored in AOVocado_global_settings.json.
        self.group2_prefixes = tuple(self.settings.GROUP2_SEARCH)
        self.group3_set = {x.lower() for x in self.settings.GROUP3_SEARCH}
        # Exclusion is case-insensitive on both exact and prefix match,
        # unlike the group2 prefix convention above.
        self.exclude_set = {x.lower() for x in self.settings.EXCLUDE_SEARCH}
        self.exclude_prefixes = tuple(
            x.lower() for x in self.settings.EXCLUDE_PREFIX_SEARCH
        )

    def is_channel_excluded(self, channel_name):
        """Checks whether a channel name should never be shown anywhere.

        Args:
            channel_name (str): A channel layer name (no ".red"/".green"/etc
                suffix - e.g. "crypto_object00", not "crypto_object00.red").

        Returns:
            bool: True if `channel_name` matches `EXCLUDE_SEARCH` (exact) or
                `EXCLUDE_PREFIX_SEARCH` (prefix), both case-insensitive.
        """
        name_lower = channel_name.lower()
        if name_lower in self.exclude_set:
            return True
        return name_lower.startswith(self.exclude_prefixes)

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

        # Extract unique channel names (before the dot), dropping anything
        # excluded via EXCLUDE_SEARCH/EXCLUDE_PREFIX_SEARCH - treated as if
        # it doesn't exist, so it never reaches any of the 4 groups.
        unique_channels = sorted(
            set(c.split(".")[0] for c in channel_list), key=lambda v: v.upper()
        )
        unique_channels = [
            c for c in unique_channels if not self.is_channel_excluded(c)
        ]

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

        _log.debug(
            "categorized %s channels: group1=%s group2=%s group3=%s group4=%s",
            len(unique_channels),
            len(groups.group_ch1),
            len(groups.group_ch2),
            len(groups.group_ch3),
            len(groups.group_ch4),
        )
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
