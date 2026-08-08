from . import config


class ChannelGroups:

    def __init__(self):

        self.list_ch1 = []
        self.list_ch2 = []
        self.list_ch3 = []
        self.list_ch4 = []

    def clear(self):

        self.list_ch1.clear()
        self.list_ch2.clear()
        self.list_ch3.clear()
        self.list_ch4.clear()


# class ChannelManager:

#     def __init__(self, settings):
#         self.settings = config
#         self.group1_set = {x.lower() for x in self.settings.GROUP1_SEARCH}
#         # Prefixes need to be a tuple for .startswith()
#         self.group2_prefixes = tuple(self.settings.GROUP2_SEARCH)
#         self.group3_set = {x.lower() for x in self.settings.GROUP3_SEARCH}

#     def categorize_channels(self, channel_list):
#         """Categorizes a list of channels into predefined groups.

#         Args:
#             channel_list (list[str]): A list of full channel names (e.g., 'rgba.red').

#         Returns:
#             ChannelGroups: An object containing categorized lists of channel layers.
#         """
#         groups = ChannelGroups()

#         # Extract unique channel names (before the dot)
#         unique_channels = sorted(
#             set(c.split(".")[0] for c in channel_list), key=lambda v: v.upper()
#         )

#         # Categorize channels based on configuration
#         for channel in unique_channels:
#             channel_lower = channel.lower()

#             if channel_lower in self.group1_set:
#                 groups.aov_ch.append(channel)
#             elif channel_lower in self.group3_set:
#                 groups.tech_ch.append(channel)
#             # .startswith can accept a tuple of prefixes
#             elif channel.startswith(self.group2_prefixes):
#                 groups.plo_ch.append(channel)
#             else:
#                 groups.other_ch.append(channel)

#         return groups

#     def collect_channels_from_viewer(self):
#         """Collects and categorizes channels from the active viewer's input.

#         Returns:
#             ChannelGroups: An object containing the categorized channels.
#         """
#         viewer_input_node = ViewerManager.get_viewer_input_node()
#         if not viewer_input_node:
#             return ChannelGroups()

#         all_channels = viewer_input_node.channels()
#         return self.categorize_channels(all_channels)
