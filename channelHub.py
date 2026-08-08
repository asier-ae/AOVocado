"""The main panel window for channelHub.

Defines `ChannelHub`, the floating Qt window that lists a viewer's channels
across 4 configurable groups and lets an artist browse/select/view them.

Author: Asier Aparicio
"""

import nuke

from . import config, constants, models, utils
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import QEvent, Qt
from ._vendor.Qt.QtWidgets import QAbstractItemView, QMainWindow


class ChannelHub(QMainWindow):
    """The channelHub panel window.

    Loads its UI from `ui_files/channelHubUI.ui` and wires up channel
    population, selection/viewing, multi-select, and search filtering
    across the 4 channel-group list widgets.

    Attributes:
        settings (config.Settings): Loaded app/user settings.
        channel_groups (models.ChannelGroups): The channels currently
            populated into the 4 lists, categorized by group.
        keyboard_state (models.KeyboardState): Tracks whether Ctrl/Shift is
            currently held, driving single- vs multi-select mode.
        viewer_manager (models.ViewerManager): Interface to the active Nuke
            viewer (get/set displayed channel, etc.).
        channel_manager (models.ChannelManager): Collects and categorizes
            channels from the viewer's input node.
        list_widgets (list[QListWidget]): The 4 channel-group list widgets,
            built once in `_setup_window()` after `loadUi()` runs.
        all_selected_items (list[QListWidgetItem]): Every currently
            selected item across all 4 lists. Order reflects list/group
            order (list_ch1's selected items, then list_ch2's, etc.) - not
            click order and not alphabetical. These are live Qt object
            references, not copies of their text - see the gotcha note
            where this is initialized below.
        last_selection (QListWidgetItem or None): The most recently
            interacted-with item, used to target Ctrl+A's select-all at the
            right group. Also a live Qt object reference, not a string.
        original_viewer_channel (str): The channel the viewer was showing
            before this panel opened, restored on close.
    """

    def __init__(self):
        """Builds core components, loads the UI, and populates the panel."""
        super().__init__()
        self.settings = config.Settings()

        # Core components
        self.channel_groups = models.ChannelGroups()
        self.keyboard_state = models.KeyboardState()
        self.viewer_manager = models.ViewerManager()
        self.channel_manager = models.ChannelManager(self.settings)

        # Selection state. Both hold QListWidgetItem objects, not strings
        # (e.g. current_item.text() is used to read the channel name out of
        # one). These are live references into the list widgets, not copies
        # - if a list is ever cleared/repopulated while something still
        # holds one of its old items here, that reference would point to a
        # deleted item. Nothing currently does that at the wrong time, but
        # watch for it if a channel-list refresh feature gets added later.
        self.all_selected_items = []
        self.last_selection = None
        self.original_viewer_channel = self.viewer_manager.get_viewer_channel()

        self._setup_window()
        self._setup_group_titles()
        self._setup_info_labels()
        self._setup_channel_lists()
        self._setup_filter()

        self._populate_channel_lists()
        self._select_current_viewer_channel()

        self.lineFilter.setFocus()

    # --- Window setup ---

    def _setup_window(self):
        """Loads the UI file and configures the main window's properties."""
        # loadUi(path, self) sets every named widget in the .ui as a direct
        # attribute on self (e.g. self.list_ch1, self.gb1, self.lineFilter)
        # - that's why this file never needs findChild() to reach them.
        loadUi(self.settings.UI_PATH, self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(constants.QWINDOW_TITLE)
        self.installEventFilter(self)
        utils._move_to_cursor(self)

        # UI widget list object names
        self.list_widgets = [self.list_ch1, self.list_ch2, self.list_ch3, self.list_ch4]

    def _setup_group_titles(self):
        """Sets the 4 group box titles from settings, not the .ui defaults.

        global_settings.json is the runtime source of truth for these
        titles - whatever text is baked into the .ui file is just a
        Designer placeholder.
        """
        self.gb1.setTitle(self.settings.GROUP1_TITLE)
        self.gb2.setTitle(self.settings.GROUP2_TITLE)
        self.gb3.setTitle(self.settings.GROUP3_TITLE)
        self.gb4.setTitle(self.settings.GROUP4_TITLE)

    def _setup_info_labels(self):
        """Sets the version/author and hotkey labels from settings."""
        self.author.setText(self.settings.get_version_line())
        self.l_hotkeys.setText(self.settings.get_hotkey_line())

    def _setup_channel_lists(self):
        """Connects selection-change handling for all 4 channel lists."""
        for list_widget in self.list_widgets:
            list_widget.itemSelectionChanged.connect(self._on_selection_changed)

    def _setup_filter(self):
        """Connects the channel search box."""
        self.lineFilter.textChanged.connect(self._filter_channels)

    # --- Channel population ---

    def _populate_channel_lists(self):
        """Loads channels from the viewer input and fills the 4 lists."""
        self.channel_groups = self.channel_manager.collect_channels_from_viewer()
        for list_widget, channels in zip(
            self.list_widgets,
            (
                self.channel_groups.group_ch1,
                self.channel_groups.group_ch2,
                self.channel_groups.group_ch3,
                self.channel_groups.group_ch4,
            ),
        ):
            list_widget.clear()
            list_widget.addItems(channels)

    def _select_current_viewer_channel(self):
        """Selects whichever channel the viewer is already showing, if listed.

        Stops at the first list where a match is found - this assumes
        channel names are unique across the 4 groups, which holds because
        ChannelManager categorizes each channel into exactly one group.
        """
        current_channel = self.viewer_manager.get_viewer_channel()
        if not current_channel:
            return
        for list_widget in self.list_widgets:
            items = list_widget.findItems(current_channel, Qt.MatchExactly)
            if items:
                items[0].setSelected(True)
                self._store_selected_items()
                return

    # --- Selection & viewing ---

    def _store_selected_items(self):
        """Gathers selected items from all 4 lists into all_selected_items.

        Resulting order is list/group order (see the all_selected_items
        docstring on the class), not click order or alphabetical.
        """
        self.all_selected_items = []
        for list_widget in self.list_widgets:
            self.all_selected_items.extend(list_widget.selectedItems())

    def _on_selection_changed(self):
        """Handles a selection change in any of the 4 channel lists.

        A plain click always shows the clicked channel in the viewer and
        clears the other 3 lists. While Ctrl/Shift is held, selections just
        accumulate across lists and the viewer is left alone.

        Gotcha: this method is reentrant. `current_item.isSelected()` is
        checked separately from `current_item` being non-None because the
        `list_widget.clearSelection()` calls below fire `itemSelectionChanged`
        synchronously - Qt does not queue this signal, so clearing another
        list's selection calls this same method again, mid-execution, once
        per list being cleared, before this outer call finishes. Those
        reentrant calls see a `current_item` that is no longer selected, so
        the `is_selected` guard turns them into safe no-ops instead of
        letting them fight the outer call over which channel the viewer
        should show. The final `_store_selected_items()` call below (after
        `set_viewer_channel`) is what produces the correct final selection
        snapshot - it relies on those reentrant clearSelection() calls
        having already completed by the time it runs.
        """
        sender = self.sender()
        current_item = sender.currentItem()
        is_selected = bool(current_item and current_item.isSelected())

        if is_selected:
            self.last_selection = current_item

        self._store_selected_items()

        if self.keyboard_state.multi_selection_active or not is_selected:
            return

        if current_item.text() == self.viewer_manager.get_viewer_channel():
            return

        for list_widget in self.list_widgets:
            if list_widget is not sender:
                list_widget.clearSelection()

        self.viewer_manager.set_viewer_channel(current_item.text())
        self._store_selected_items()

    def _select_all_in_active_group(self):
        """Selects every channel in the group that was last interacted with.

        Relies on the caller (keyPressEvent) only invoking this while Ctrl
        is held, since that's what puts the target list into
        ExtendedSelection mode - selectAll() on a SingleSelection list
        would not actually select everything.
        """
        if self.all_selected_items and self.last_selection:
            self.last_selection.listWidget().selectAll()
            self._store_selected_items()

    # --- Multi-select mode (keyboard-driven) ---

    def _set_selection_mode(self, multi):
        """Switches all 4 lists between single- and multi-selection.

        Args:
            multi (bool): True for ExtendedSelection (Ctrl/Shift-click
                accumulates), False for SingleSelection.
        """
        mode = (
            QAbstractItemView.ExtendedSelection
            if multi
            else QAbstractItemView.SingleSelection
        )
        for list_widget in self.list_widgets:
            list_widget.setSelectionMode(mode)

    def event(self, event):
        """Claims Ctrl/Cmd+A before Qt's global shortcut dispatch runs.

        Without this, Qt lets a competing QAction/QShortcut elsewhere in the
        app (e.g. Nuke's Node Graph "Select All") win the key combo before
        keyPressEvent ever sees it - most noticeable on macOS, where Qt
        merges menu shortcuts into the shared system menu bar. keyPressEvent
        is what actually runs the select-all logic afterward; removing this
        override silently breaks Ctrl+A on Mac while leaving the code
        looking correct and working fine on Linux/Windows.

        Args:
            event (QEvent): The incoming Qt event.

        Returns:
            bool: True if this event was fully handled here, otherwise the
            base QMainWindow.event() result.
        """
        if event.type() == QEvent.ShortcutOverride:
            if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event):
        """Handles Ctrl+A select-all and tracks Ctrl/Shift for multi-select.

        Ctrl+A is handled directly here (in cooperation with the `event()`
        override above) rather than via a QShortcut, since a QShortcut for
        this combo loses to Nuke's own Node Graph "Select All" on macOS.

        Args:
            event (QKeyEvent): The key press event.
        """
        if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self._select_all_in_active_group()
            return

        was_active = self.keyboard_state.multi_selection_active
        self.keyboard_state.update_key_press(event.key())
        if self.keyboard_state.multi_selection_active and not was_active:
            self._set_selection_mode(True)

    def keyReleaseEvent(self, event):
        """Tracks Ctrl/Shift release, reverting to single-select once both are up.

        Args:
            event (QKeyEvent): The key release event.
        """
        self.keyboard_state.update_key_release(event.key())
        if not self.keyboard_state.multi_selection_active:
            self._set_selection_mode(False)

    def eventFilter(self, obj, event):
        """Resets multi-select state when the panel loses focus.

        Prevents the panel from getting stuck in multi-select mode if focus
        is lost mid Ctrl/Shift-hold (e.g. alt-tabbing away), since the
        corresponding keyReleaseEvent would never arrive in that case.

        Args:
            obj (QObject): The watched object (this window, via
                installEventFilter(self)).
            event (QEvent): The event being filtered.

        Returns:
            bool: Always False - this filter only observes events, it never
            consumes them.
        """
        if event.type() == QEvent.WindowDeactivate:
            self.keyboard_state.reset()
            self._set_selection_mode(False)
        return False

    # --- Filtering ---

    def _filter_channels(self):
        """Hides channels that don't match the current search text.

        Uses setRowHidden, which only affects visibility, not the selection
        model - a selected item that gets filtered out stays selected (just
        invisible). Worth knowing before debugging any
        selection-looks-wrong-after-search reports.
        """
        filter_text = self.lineFilter.text().lower()
        for list_widget in self.list_widgets:
            for row in range(list_widget.count()):
                item = list_widget.item(row)
                list_widget.setRowHidden(row, filter_text not in item.text().lower())

    # --- Qt event overrides ---

    def closeEvent(self, event):
        """Restores the original viewer channel and resets the Nuke panel flag.

        Args:
            event (QCloseEvent): The close event.
        """
        self.viewer_manager.set_viewer_channel(self.original_viewer_channel)
        setattr(nuke, constants.NUKE_PANEL_NAME, False)
