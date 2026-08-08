import nuke

from . import config, constants, models, utils
from ._vendor.Qt.QtCompat import loadUi
from ._vendor.Qt.QtCore import QEvent, Qt
from ._vendor.Qt.QtWidgets import QAbstractItemView, QMainWindow


class ChannelHub(QMainWindow):

    LIST_WIDGETS = ["list_ch1", "list_ch2", "list_ch3", "list_ch4"]

    def __init__(self):
        super().__init__()
        self.settings = config.Settings()

        # Core components
        self.channel_groups = models.ChannelGroups()
        self.keyboard_state = models.KeyboardState()
        self.viewer_manager = models.ViewerManager()
        self.channel_manager = models.ChannelManager(self.settings)

        # Selection state
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
        loadUi(self.settings.UI_PATH, self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(constants.QWINDOW_TITLE)
        self.installEventFilter(self)
        utils._move_to_cursor(self)

    def _setup_group_titles(self):
        """Sets the 4 group box titles from settings, not the .ui defaults."""
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
        for list_widget in self._get_all_list_widgets():
            list_widget.itemSelectionChanged.connect(self._on_selection_changed)

    def _setup_filter(self):
        """Connects the channel search box."""
        self.lineFilter.textChanged.connect(self._filter_channels)

    # --- Channel population ---

    def _populate_channel_lists(self):
        """Loads channels from the viewer input and fills the 4 lists."""
        self.channel_groups = self.channel_manager.collect_channels_from_viewer()
        for list_widget, channels in zip(
            self._get_all_list_widgets(),
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
        """Selects whichever channel the viewer is already showing, if listed."""
        current_channel = self.viewer_manager.get_viewer_channel()
        if not current_channel:
            return
        for list_widget in self._get_all_list_widgets():
            items = list_widget.findItems(current_channel, Qt.MatchExactly)
            if items:
                items[0].setSelected(True)
                self._store_selected_items()
                return

    # --- Selection & viewing ---

    def _get_all_list_widgets(self):
        """Returns the 4 channel QListWidgets."""
        return [getattr(self, name) for name in self.LIST_WIDGETS]

    def _store_selected_items(self):
        """Gathers selected items from all 4 lists into all_selected_items."""
        self.all_selected_items = []
        for list_widget in self._get_all_list_widgets():
            self.all_selected_items.extend(list_widget.selectedItems())

    def _on_selection_changed(self):
        """Handles a selection change in any of the 4 channel lists.

        A plain click always shows the clicked channel in the viewer and
        clears the other 3 lists. While Ctrl/Shift is held, selections just
        accumulate across lists and the viewer is left alone.
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

        for list_widget in self._get_all_list_widgets():
            if list_widget is not sender:
                list_widget.clearSelection()

        self.viewer_manager.set_viewer_channel(current_item.text())
        self._store_selected_items()

    def _select_all_in_active_group(self):
        """Selects every channel in the group that was last interacted with."""
        if self.all_selected_items and self.last_selection:
            self.last_selection.listWidget().selectAll()
            self._store_selected_items()

    # --- Multi-select mode (keyboard-driven) ---

    def _set_selection_mode(self, multi):
        """Switches all 4 lists between single- and multi-selection."""
        mode = (
            QAbstractItemView.ExtendedSelection
            if multi
            else QAbstractItemView.SingleSelection
        )
        for list_widget in self._get_all_list_widgets():
            list_widget.setSelectionMode(mode)

    def event(self, event):
        """Claims Ctrl/Cmd+A before Qt's global shortcut dispatch runs.

        Without this, Qt lets a competing QAction/QShortcut elsewhere in the
        app (e.g. Nuke's Node Graph "Select All") win the key combo before
        keyPressEvent ever sees it - most noticeable on macOS, where Qt
        merges menu shortcuts into the shared system menu bar.
        """
        if event.type() == QEvent.ShortcutOverride:
            if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            self._select_all_in_active_group()
            return

        was_active = self.keyboard_state.multi_selection_active
        self.keyboard_state.update_key_press(event.key())
        if self.keyboard_state.multi_selection_active and not was_active:
            self._set_selection_mode(True)

    def keyReleaseEvent(self, event):
        self.keyboard_state.update_key_release(event.key())
        if not self.keyboard_state.multi_selection_active:
            self._set_selection_mode(False)

    def eventFilter(self, obj, event):
        """Resets multi-select state when the panel loses focus."""
        if event.type() == QEvent.WindowDeactivate:
            self.keyboard_state.reset()
            self._set_selection_mode(False)
        return False

    # --- Filtering ---

    def _filter_channels(self):
        """Hides channels that don't match the current search text."""
        filter_text = self.lineFilter.text().lower()
        for list_widget in self._get_all_list_widgets():
            for row in range(list_widget.count()):
                item = list_widget.item(row)
                list_widget.setRowHidden(row, filter_text not in item.text().lower())

    # --- Qt event overrides ---

    def closeEvent(self, event):
        """Restores the original viewer channel and resets the Nuke panel flag."""
        self.viewer_manager.set_viewer_channel(self.original_viewer_channel)
        setattr(nuke, constants.NUKE_PANEL_NAME, False)
