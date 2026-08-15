"""Wires an AOVocado panel to a LiveSampler instance.

Owns the LiveSampler, sets up the sampler button and threshold spinbox on
the panel, and reacts to the sampler's signals to update the panel's
widgets (filtering the channel lists to detected channels, restoring state
when sampling stops). Kept separate from AOVocado.py since this is a
self-contained feature with a fair amount of UI-reaction logic of its own.

Author: Asier Aparicio
"""

from . import live_sampler, logger, utils
from ._vendor.Qt.QtCore import Qt
from ._vendor.Qt.QtWidgets import QMessageBox

_log = logger.get_logger(__name__)


class SamplerController:
    """Connects an AOVocado panel's sampler UI to a LiveSampler.

    Attributes:
        panel (AOVocado.AOVocado): The panel this is wired to.
        live_sampler (live_sampler.LiveSampler): The sampling state machine.
    """

    def __init__(self, panel):
        """Builds the LiveSampler and wires up the panel's sampler widgets.

        Args:
            panel (AOVocado.AOVocado): The panel to control. Must expose
                `b_live_sampler`, `sp_sampler_thresh`, `lineFilter`,
                `list_widgets`, `channel_groups`, `all_selected_items`,
                `viewer_manager`, and `settings`.
        """
        self.panel = panel
        self.live_sampler = live_sampler.LiveSampler(panel.viewer_manager, parent=panel)

        self._setup_threshold_control()
        self._setup_sampler_button()
        self._connect_signals()

    def _setup_threshold_control(self):
        """Seeds the threshold spinbox from settings and hides it until sampling starts."""
        threshold_field = self.panel.sp_sampler_thresh
        threshold_field.setValue(
            self.panel.settings.my_settings["user_settings"]["cfg_sp_sampler_threshold"]
        )
        threshold_field.setVisible(False)
        threshold_field.valueChanged.connect(self._on_threshold_changed)

    def _setup_sampler_button(self):
        """Configures the sampler toggle button's icon, tooltip, and click handler."""
        button = self.panel.b_live_sampler
        button.setCheckable(True)
        utils.set_button_icon(
            button,
            self.panel.settings.ICON_SAMPLE,
            tooltip=(
                "Start viewer sampler. This will filter the channels.\n"
                "Just Ctrl+click on the image"
            ),
        )
        button.toggled.connect(self._on_toggled)

    def _connect_signals(self):
        """Connects the LiveSampler's signals to this controller's handlers."""
        self.live_sampler.samplingStarted.connect(self._on_sampling_started)
        self.live_sampler.samplingStopped.connect(self._on_sampling_stopped)
        self.live_sampler.resultsReady.connect(self._on_results_ready)
        self.live_sampler.errorOccurred.connect(self._on_error)

    def _on_toggled(self, checked):
        """Starts or stops sampling based on the button's new checked state.

        Args:
            checked (bool): The button's new checked state.
        """
        _log.debug("sampler button toggled: %s", checked)
        if checked:
            self.live_sampler.start(self.panel.all_selected_items)
        else:
            self.live_sampler.stop()

    def _on_threshold_changed(self):
        """Forces an immediate re-sample when the threshold changes mid-sample."""
        if self.live_sampler.is_active:
            _log.debug(
                "threshold changed to %s - forcing re-sample",
                self.panel.sp_sampler_thresh.value(),
            )
            self.live_sampler.last_sampled_bbox = None  # Force an update
            self.live_sampler._update_loop()

    def _on_sampling_started(self):
        """Updates the panel's widgets for the start of sampling."""
        panel = self.panel
        panel.lineFilter.clear()
        panel.lineFilter.setEnabled(False)
        panel.sp_sampler_thresh.setVisible(True)
        panel.b_live_sampler.setStyleSheet("background-color: green;")
        panel.b_live_sampler.setIcon(utils.load_icon(panel.settings.ICON_SAMPLE_WHITE))
        panel.b_live_sampler.setToolTip("Stop live channel filter")

    def _on_sampling_stopped(self, prev_selection_names, prev_channel):
        """Restores the panel's widgets and prior selection/channel.

        Args:
            prev_selection_names (list[str]): Channel names selected before
                sampling started.
            prev_channel (str): The viewer channel shown before sampling started.
        """
        panel = self.panel
        panel.lineFilter.setEnabled(True)
        panel.sp_sampler_thresh.setVisible(False)
        panel.b_live_sampler.setStyleSheet("")
        panel.b_live_sampler.setIcon(utils.load_icon(panel.settings.ICON_SAMPLE))
        panel.b_live_sampler.setToolTip(
            "Start viewer sampler. This will filter the channels.\n"
            "Just Ctrl+click on the image"
        )

        panel.refresh_list_widgets()
        panel.viewer_manager.set_viewer_channel(prev_channel)
        panel.select_channels_by_name(prev_selection_names)

    def _on_results_ready(self, detected_channels, new_viewer_channel):
        """Filters the panel's lists to the detected channels and views the strongest one.

        Args:
            detected_channels (list[tuple]): (channel_name, value) pairs,
                sorted by value descending.
            new_viewer_channel (str): The channel to display in the viewer.
        """
        panel = self.panel
        if panel.viewer_manager.get_viewer_channel() != new_viewer_channel:
            panel.viewer_manager.set_viewer_channel(new_viewer_channel)

        detected_names = [ch for ch, val in detected_channels]

        # Signals blocked for the whole repopulate+select, same as the
        # rest of this codebase's bulk-update pattern - this runs on a
        # ~10Hz timer while sampling, so avoiding a full selection-changed
        # cascade per tick matters here more than most places.
        for list_widget in panel.list_widgets:
            list_widget.blockSignals(True)
        panel.show_detected_channels(detected_names)
        for list_widget in panel.list_widgets:
            for item in list_widget.findItems(new_viewer_channel, Qt.MatchExactly):
                item.setSelected(True)
        for list_widget in panel.list_widgets:
            list_widget.blockSignals(False)
        panel._store_selected_items()

    def _on_error(self, message):
        """Unchecks the sampler button and shows the error to the user.

        Args:
            message (str): The error message to display.
        """
        self.panel.b_live_sampler.setChecked(False)
        QMessageBox.warning(self.panel, "Live Sampler Error", message)
