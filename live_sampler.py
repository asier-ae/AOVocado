# Copyright (c) 2026 Asier Aparicio
# Licensed under the MIT License.

"""The live channel sampler's state machine.
"""

import nuke

from . import live_sampler_channels, logger
from ._vendor.Qt.QtCore import QObject, QTimer, Signal

_log = logger.get_logger(__name__)


class LiveSampler(QObject):
    """A state machine for managing the live channel sampling process.

    Encapsulates starting, stopping, and updating the live sampling. Uses a
    QTimer to periodically check the viewer and emits signals to communicate
    with the main UI (see `live_sampler_controller.py`), keeping this state
    machine decoupled from any specific window's widgets.

    Attributes:
        samplingStarted (Signal): Emitted when sampling begins.
        samplingStopped (Signal): Emitted when sampling stops, returning the
            pre-sample state (selection and channel).
        resultsReady (Signal): Emitted when new sample results are available.
        errorOccurred (Signal): Emitted when an error occurs during sampling.
    """

    samplingStarted = Signal()
    samplingStopped = Signal(list, str)  # Emits pre-sample selection and channel
    resultsReady = Signal(list, str)  # Emits detected channels and new viewer channel
    errorOccurred = Signal(str)  # Emits an error message string

    def __init__(self, viewer_manager, parent=None):
        """Initializes the LiveSampler.

        Args:
            viewer_manager (viewer.ViewerManager): Interface to the Nuke viewer.
            parent (QObject, optional): The parent Qt object. Must expose a
                `sp_sampler_thresh` widget (the threshold spinbox) - see
                `_update_loop()`. Defaults to None.
        """
        super().__init__(parent)
        self.viewer_manager = viewer_manager
        self.last_sampled_bbox = None
        self.is_active = False

        # The sampler owns its own timer
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._update_loop)

        # Store pre-sampling state
        self._pre_sample_viewer_channel = None
        self._pre_sample_selected_items = []

    def start(self, current_selection):
        """Starts the live sampling process.

        Stores the current UI state, starts the timer, and emits the
        `samplingStarted` signal.

        Args:
            current_selection (list): A list of the currently selected
                QListWidgetItems from the main UI.
        """
        # Store the state of the UI before starting
        self._pre_sample_viewer_channel = self.viewer_manager.get_viewer_channel()
        self._pre_sample_selected_items = [item.text() for item in current_selection]
        _log.debug(
            "start: pre_sample_channel=%s pre_sample_selection=%s",
            self._pre_sample_viewer_channel,
            self._pre_sample_selected_items,
        )

        # Start the timer and update state
        self.is_active = True
        self.last_sampled_bbox = None  # Reset bbox to force initial sample
        self._timer.start()

        # Emit a signal to let the UI know we have started
        self.samplingStarted.emit()

        # Run the first sample immediately
        self.viewer_manager.set_viewer_channel("rgba")
        self._update_loop()

    def stop(self):
        """Stops the live sampling process.

        Stops the timer and emits the `samplingStopped` signal with the
        pre-sample state to allow the UI to restore itself.
        """
        _log.debug("stop")
        self._timer.stop()
        self.is_active = False
        self.viewer_manager.set_viewer_channel("rgba")

        # Emit a signal with the pre-sample state so the UI can restore itself
        self.samplingStopped.emit(
            self._pre_sample_selected_items, self._pre_sample_viewer_channel
        )

    def _update_loop(self):
        """The internal loop called by the timer to perform sampling.

        Checks if the mouse position has changed, performs the channel
        sampling, and emits the `resultsReady` signal with the findings.
        """
        try:
            viewer = nuke.activeViewer()
            if not viewer:
                return

            view_node = viewer.node()
            current_bbox = view_node["colour_sample_bbox"].value()

            if str(current_bbox) == self.last_sampled_bbox:
                return
            self.last_sampled_bbox = str(current_bbox)

            threshold = self.parent().sp_sampler_thresh.value()

            detected_channels = live_sampler_channels.sample_viewer_channels(
                threshold=threshold, channel_manager=self.parent().channel_manager
            )
            detected_names = [ch for ch, val in detected_channels]
            new_viewer_channel = self._get_fallback_channel(detected_names)

            self.resultsReady.emit(detected_channels, new_viewer_channel)

        except Exception:
            _log.exception("Live sampling error")
            self.stop()  # Stop on error

    def _get_fallback_channel(self, detected_names):
        """Determines the best channel to display in the viewer.

        Prioritizes the current channel, then 'rgba', then the channel with
        the highest value.

        Args:
            detected_names (list[str]): A list of detected channel names.

        Returns:
            str: The name of the channel to set in the viewer.
        """
        viewer_channel = self.viewer_manager.get_viewer_channel()
        if viewer_channel in detected_names:
            return viewer_channel
        if "rgba" in detected_names:
            return "rgba"
        if detected_names:
            return detected_names[0]
        return viewer_channel
