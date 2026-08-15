"""The main panel window for channelHub.

Defines `ChannelHub`, the floating Qt window that lists a viewer's channels
across 4 configurable groups and lets an artist browse/select/view them.

Author: Asier Aparicio
"""

import nuke

from . import (
    channels,
    config,
    constants,
    keyboard_state,
    logger,
    node_creation,
    rebuild_subtractive,
    sampler_controller,
    utils,
    viewer,
)
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import QEvent, Qt
from ._vendor.Qt.QtGui import QKeySequence
from ._vendor.Qt.QtWidgets import QAbstractItemView, QMainWindow, QMessageBox
from .settings_window import SettingsWindow

_log = logger.get_logger(__name__)


class ChannelHub(QMainWindow):
    """The channelHub panel window.

    Loads its UI from `ui_files/channelHubUI.ui` and wires up channel
    population, selection/viewing, multi-select, and search filtering
    across the 4 channel-group list widgets, plus the 4 node-creation
    buttons and the settings button that opens `SettingsWindow`.

    Attributes:
        settings (config.Settings): Loaded app/user settings.
        channel_groups (channels.ChannelGroups): The channels currently
            populated into the 4 lists, categorized by group.
        keyboard_state (keyboard_state.KeyboardState): Tracks whether
            Ctrl/Shift is currently held, driving single- vs multi-select mode.
        viewer_manager (viewer.ViewerManager): Interface to the active Nuke
            viewer (get/set displayed channel, etc.).
        channel_manager (channels.ChannelManager): Collects and categorizes
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
        sampler_controller (sampler_controller.SamplerController): Owns the
            live channel sampler and its UI reactions - see that module.
    """

    def __init__(self):
        """Builds core components, loads the UI, and populates the panel."""
        _log.debug("ChannelHub.__init__ starting")
        super().__init__()
        self.settings = config.Settings()

        # Core components
        self.channel_groups = channels.ChannelGroups()
        self.keyboard_state = keyboard_state.KeyboardState()
        self.viewer_manager = viewer.ViewerManager()
        self.channel_manager = channels.ChannelManager(self.settings)

        # Selection state. Both hold QListWidgetItem objects, not strings
        # (e.g. current_item.text() is used to read the channel name out of
        # one). These are live references into the list widgets, not copies
        # - if a list is ever cleared/repopulated while something still
        # holds one of its old items here, that reference would point to a
        # deleted item. _populate_channel_lists() resets both before
        # clearing the lists, for exactly this reason - see reload_channels().
        self.all_selected_items = []
        self.last_selection = None
        self.original_viewer_channel = self.viewer_manager.get_viewer_channel()

        self._setup_window()
        self._setup_group_titles()
        self._setup_info_labels()
        self._setup_channel_lists()
        self._setup_filter()
        self._setup_node_creation_buttons()
        self._setup_settings_button()
        self._setup_copy_button()
        self._setup_split_subtractive_button()
        self._setup_sampler()
        self._setup_viewer_callback()

        self._populate_channel_lists()
        self._select_current_viewer_channel()

        self.lineFilter.setFocus()
        _log.debug("ChannelHub.__init__ complete")

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

        # Built once, here, since the widgets don't exist until loadUi()
        # has run above, and never change after this - every other method
        # that needs "all 4 lists" just reads this instead of re-resolving
        # the widgets each time.
        self.list_widgets = [self.list_ch1, self.list_ch2, self.list_ch3, self.list_ch4]

    def _setup_group_titles(self):
        """Sets the 4 group box titles from settings, not the .ui defaults.

        channelHub_global_settings.json is the runtime source of truth for these
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

    def _setup_node_creation_buttons(self):
        """Configures the 4 node-creation buttons and their mode toggles.

        Button text and each mode toggle's initial checked state come from
        settings (BUTTON1..4_TITLE / _ICONMODE) - the .ui file's own text is
        just a Designer placeholder, same convention as the group titles.
        """
        user_settings = self.settings.my_settings["user_settings"]
        for i in range(1, 5):
            prefix = f"BUTTON{i}"
            button = getattr(self, f"b{i}")
            mode_button = getattr(self, f"b{i}_mode")

            button.setText(user_settings[f"{prefix}_TITLE"])
            button.clicked.connect(self._on_create_node_clicked)

            mode_button.setText("")
            mode_button.setChecked(user_settings[f"{prefix}_ICONMODE"])
            mode_button.toggled.connect(
                lambda checked, b=mode_button: self._update_mode_button(b)
            )
            self._update_mode_button(mode_button)

    def _update_mode_button(self, button):
        """Refreshes one mode button's icon/tooltip to match its checked state.

        Args:
            button (QPushButton): The mode button that changed.
        """
        utils.update_mode_button_visuals(
            button, self.settings.ICON_H_MODE, self.settings.ICON_V_MODE
        )

    def _setup_settings_button(self):
        """Configures the settings button's icon and click handler."""
        utils.set_button_icon(
            self.b_show_settings, self.settings.ICON_SETTINGS, size=21
        )
        self.b_show_settings.clicked.connect(self._on_show_settings)

    def _setup_copy_button(self):
        """Configures the copy-to-clipboard button's icon and click handler."""
        utils.set_button_icon(
            self.b_copy,
            self.settings.ICON_COPY,
            tooltip="Copy selected channel names to clipboard",
        )
        self.b_copy.clicked.connect(self._on_copy_to_clipboard)

    def _setup_split_subtractive_button(self):
        """Configures the subtractive-rebuild button's icon and click handler."""
        # 27px fills the button without touching its edges - Qt's default
        # button icon size looks tiny/off-center at this button's 30x30.
        utils.set_button_icon(
            self.b_split_subtractive, self.settings.ICON_SPLIT_SUBTRACTIVE, size=27
        )
        self.b_split_subtractive.clicked.connect(self._on_split_subtractive_clicked)

    def _setup_sampler(self):
        """Creates the live sampler and wires it to this panel (see sampler_controller.py)."""
        self.sampler_controller = sampler_controller.SamplerController(self)

    def _setup_viewer_callback(self):
        """Registers the viewer-input-change callback (see viewer.py)."""
        self.viewer_manager.enable_reload_callback()

    # --- Channel population ---

    def _populate_channel_lists(self):
        """Loads channels from the viewer input and fills the 4 lists."""
        # Reset first: refresh_list_widgets()'s list_widget.clear() calls
        # destroy the QListWidgetItem objects these might still be
        # referencing (see the gotcha note on these attributes in
        # __init__) - reload_channels() is exactly the "channel-list
        # refresh feature" that note warned about, so this can no longer
        # only run once, at construction.
        self.all_selected_items = []
        self.last_selection = None

        self.channel_groups = self.channel_manager.collect_channels_from_viewer()
        _log.debug(
            "populated lists: group1=%s group2=%s group3=%s group4=%s",
            len(self.channel_groups.group_ch1),
            len(self.channel_groups.group_ch2),
            len(self.channel_groups.group_ch3),
            len(self.channel_groups.group_ch4),
        )
        self.refresh_list_widgets()

    def refresh_list_widgets(self):
        """Redraws the 4 lists from the current `channel_groups`.

        Doesn't re-fetch from the viewer - used to restore the full
        alphabetical list after the live sampler's filtered view
        (`sampler_controller.py`), where `channel_groups` hasn't changed,
        just what's currently displayed.
        """
        for list_widget, channel_names in zip(
            self.list_widgets,
            (
                self.channel_groups.group_ch1,
                self.channel_groups.group_ch2,
                self.channel_groups.group_ch3,
                self.channel_groups.group_ch4,
            ),
        ):
            list_widget.clear()
            list_widget.addItems(channel_names)

    def show_detected_channels(self, detected_names):
        """Redisplays only the given channels, in their given order.

        Used by the live sampler to show just the channels it detected,
        strongest first (see `sampler_controller.py`) - iterates
        `detected_names` filtered by each group's set, not each group's own
        list filtered by a detected-set, specifically to preserve that
        value-sorted order rather than silently reverting to alphabetical.

        Args:
            detected_names (list[str]): Channel names to display, in the
                order they should appear.
        """
        group_sets = (
            set(self.channel_groups.group_ch1),
            set(self.channel_groups.group_ch2),
            set(self.channel_groups.group_ch3),
            set(self.channel_groups.group_ch4),
        )
        for list_widget, group_set in zip(self.list_widgets, group_sets):
            list_widget.clear()
            list_widget.addItems([name for name in detected_names if name in group_set])

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

    def reload_channels(self):
        """Repopulates the 4 lists from the viewer's (possibly new) input.

        Called by `viewer.viewer_updated()` when the viewer's connected input
        changes. Re-selects whichever channel(s) were selected before the
        reload, by name, if they still exist in the new channel set - the
        viewer's displayed channel doesn't change on its own when its input
        does, but the QListWidgetItem it pointed to gets destroyed by
        _populate_channel_lists(), so it has to be re-found by name rather
        than reusing the old item reference. Falls back to selecting
        whatever the viewer is currently showing if none of the previous
        selection is found (e.g. the new input doesn't have that channel).
        The search filter text is preserved either way.
        """
        previous_channels = list(
            dict.fromkeys(item.text() for item in self.all_selected_items)
        )
        filter_text = self.lineFilter.text()
        _log.debug("reload_channels: previous selection=%s", previous_channels)

        self._populate_channel_lists()
        if filter_text:
            self._filter_channels()

        if not self.select_channels_by_name(previous_channels):
            self._select_current_viewer_channel()

    def select_channels_by_name(self, names):
        """Selects the given channel names across the 4 lists, if found.

        Used by `reload_channels()` above and by the live sampler
        (`sampler_controller.py`) to restore a selection by name rather
        than by item reference - both cases repopulate the lists first,
        which destroys the old `QListWidgetItem`s.

        Args:
            names (list[str]): Channel names to select.

        Returns:
            bool: True if at least one name was found and selected.
        """
        found_items = []
        for name in names:
            for list_widget in self.list_widgets:
                found_items.extend(list_widget.findItems(name, Qt.MatchExactly))

        if not found_items:
            return False

        # Bulk-restore with signals blocked, then sync state once at the
        # end - otherwise _on_selection_changed's single-select
        # cross-list-clearing logic would fire per item and undo earlier
        # items in this same restore. ExtendedSelection first so Qt itself
        # doesn't also reject multiple selected items within one list.
        self._set_selection_mode(True)
        for list_widget in self.list_widgets:
            list_widget.blockSignals(True)
        for item in found_items:
            item.setSelected(True)
        for list_widget in self.list_widgets:
            list_widget.blockSignals(False)
        self._set_selection_mode(self.keyboard_state.multi_selection_active)
        self._store_selected_items()
        return True

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

    def _matches_hotkey(self, event):
        """Checks whether a key event matches the configured open/close hotkey.

        Args:
            event (QKeyEvent): The key event to check.

        Returns:
            bool: True if `event` matches `self.settings.HOTKEY`.
        """
        try:
            modifiers = int(event.modifiers())
        except TypeError:
            # PySide6's Qt.KeyboardModifier isn't directly int()-able like
            # PySide2's was - .value is the escape hatch there.
            modifiers = int(event.modifiers().value)
        pressed = QKeySequence(event.key() | modifiers)
        return pressed == QKeySequence(self.settings.HOTKEY)

    def keyPressEvent(self, event):
        """Handles the close hotkey, Ctrl+A select-all, and Ctrl/Shift tracking.

        The hotkey is checked here (not just via Nuke's own menu dispatch)
        because Nuke's hotkey system only fires while a Nuke window has OS
        focus - pressing the same combo while this floating panel itself is
        focused would otherwise do nothing, since the keypress goes to this
        widget instead. Ctrl+A is handled directly here (in cooperation with
        the `event()` override above) rather than via a QShortcut, since a
        QShortcut for this combo loses to Nuke's own Node Graph "Select All"
        on macOS.

        Args:
            event (QKeyEvent): The key press event.
        """
        if self._matches_hotkey(event):
            self.close()
            return

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

    # --- Node creation & settings ---

    def _on_create_node_clicked(self):
        """Creates nodes from the selected channels using the clicked button's settings.

        Reads the node class/knob and the corresponding mode toggle's
        checked state (horizontal vs vertical) from settings, keyed off
        which button (b1..b4) was clicked - e.g. clicking `b2` uses
        `BUTTON2_CLASS`/`BUTTON2_KNOB`/`b2_mode`. If the button's source is
        a toolset path rather than a node class, the path is re-validated
        here before creating anything - `settings_window.py` already
        blocks saving an invalid one, but this catches the file having
        changed on disk since it was saved, without partially creating
        nodes for some channels and not others.
        """
        if not self.all_selected_items:
            return

        sender_name = self.sender().objectName()
        prefix = "BUTTON" + sender_name[1:]
        mode_button = getattr(self, f"{sender_name}_mode")

        user_settings = self.settings.my_settings["user_settings"]
        node_class = user_settings[f"{prefix}_CLASS"]
        node_knob = user_settings[f"{prefix}_KNOB"]
        node_source = user_settings[f"{prefix}_SOURCE"]

        if node_source == node_creation.SOURCE_TOOLSET:
            problem = utils.validate_toolset_path(node_class)
            if problem:
                _log.debug("_on_create_node_clicked: blocked - %s", problem)
                QMessageBox.warning(self, "Invalid Toolset Path", problem)
                return

        # Deduplicated, order preserved - all_selected_items can contain the
        # same channel twice if it somehow got selected in more than one list.
        channel_names = list(
            dict.fromkeys(item.text() for item in self.all_selected_items)
        )

        mode = "horizontal" if mode_button.isChecked() else "vertical"
        _log.debug(
            "_on_create_node_clicked: button=%s class=%s source=%s mode=%s channels=%s",
            sender_name,
            node_class,
            node_source,
            mode,
            len(channel_names),
        )

        if mode_button.isChecked():
            node_creation.create_nodes_horizontal(
                node_class,
                node_knob,
                channel_names,
                user_settings["cfg_main_h_sep"],
                user_settings["cfg_main_v_sep"],
                source=node_source,
            )
        else:
            node_creation.create_node_vertical(
                node_class,
                node_knob,
                channel_names,
                source=node_source,
                v_sep=user_settings["cfg_main_v_sep"],
            )

    def _on_split_subtractive_clicked(self):
        """Builds a subtractive rebuild network from the selected channels."""
        if not self.all_selected_items:
            return

        channel_names = list(
            dict.fromkeys(item.text() for item in self.all_selected_items)
        )
        _log.debug("_on_split_subtractive_clicked: channels=%s", len(channel_names))
        rebuild_subtractive.create_subtractive_rebuild(channel_names, self.settings)
        self.close()

    def _on_show_settings(self):
        """Opens the Settings window and closes this panel.

        Closed rather than left open alongside the Settings window because
        this panel reads settings once at construction - it wouldn't reflect
        any changes made in the Settings window until reopened anyway.
        """
        _log.debug("_on_show_settings: opening Settings window")
        settings_window = SettingsWindow()
        settings_window.move(self.pos())
        constants.GC_PROTECT.append(settings_window)
        settings_window.show()
        self.close()

    def _on_copy_to_clipboard(self):
        """Copies the selected channel names to the clipboard, one per line."""
        channel_names = dict.fromkeys(item.text() for item in self.all_selected_items)
        utils.copy_to_clipboard("\n".join(channel_names))

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
        """Stops the sampler, restores the original viewer channel, and
        cleans up panel state.

        Args:
            event (QCloseEvent): The close event.
        """
        _log.debug("closeEvent")
        # Only if actually active: LiveSampler.stop() unconditionally sets
        # the viewer channel and emits samplingStopped with its pre-sample
        # state, which - if sampling was never started - is still the
        # constructor's (None, []) defaults. That would make
        # sampler_controller's handler try to set the viewer channel to
        # None. The very next line here would still overwrite it with the
        # correct value regardless, but there's no reason to risk it.
        if self.sampler_controller.live_sampler.is_active:
            self.sampler_controller.live_sampler.stop()
        self.viewer_manager.set_viewer_channel(self.original_viewer_channel)
        self.viewer_manager.remove_callback()
        setattr(nuke, constants.NUKE_PANEL_NAME, False)
