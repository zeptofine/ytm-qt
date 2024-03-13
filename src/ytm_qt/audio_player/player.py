import sys
from datetime import timedelta
from pathlib import Path
from pprint import pprint

from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
)
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractSlider,
    QApplication,
    QDockWidget,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ytm_qt import Fonts, Icons
from ytm_qt.audio_player.control_buttons import ControlButtons
from ytm_qt.playlist_generators.track_manager import TrackManager

from .audio_player import AudioPlayer


class TrackedSlider(QSlider):
    force_slide = Signal(int)

    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None) -> None:
        super().__init__(orientation, parent)
        self.sliderReleased.connect(self._sliderReleased)

    def _sliderReleased(self):
        self.force_slide.emit(self.value())

    def setValue(self, arg__1: int) -> None:
        if not self.isSliderDown():
            super().setValue(arg__1)


class Player(QWidget):
    def __init__(self, icons: Icons, fonts: Fonts, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.fonts = fonts

        self.controller = ControlButtons(self.icons, parent=self)
        self.controller.next.connect(self.move_next)
        self.controller.play.connect(self.resume)
        self.controller.pause.connect(self.pause)
        self.controller.back.connect(self.move_previous)

        self.time = timedelta(milliseconds=0)
        self.duration = timedelta(milliseconds=0)
        self.progress_bar = TrackedSlider(Qt.Orientation.Horizontal, self)
        self.progress_bar.force_slide.connect(lambda x: print(f"Force slid: {x}"))
        self.progress_display = QLabel(self)
        self.update_duration_display()

        self.manager = None
        self.audio_player = AudioPlayer(QMediaDevices.defaultAudioOutput())  # TODO: Make this configurable
        self.audio_player.duration_changed.connect(self.progress_bar.setMaximum)
        self.audio_player.progress_changed.connect(self.progress_bar.setValue)
        self.audio_player.progress_changed.connect(self.update_duration_display)
        self.audio_player.mediastatus_changed.connect(self.media_status_changed)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setMinimum(0)
        self.volume_slider.valueChanged.connect(lambda v: self.audio_player.media_output.setVolume(v / 100))
        self.volume_slider.setValue(100)
        self.previous_label = QLabel(self)
        self.current_label = QLabel(self)
        self.next_label = QLabel(self)

        self.layout_ = QGridLayout(self)
        self.layout_.addWidget(self.previous_label, 0, 0, 1, 3)
        self.layout_.addWidget(self.current_label, 1, 0, 1, 3)
        self.layout_.addWidget(self.next_label, 2, 0, 1, 3)
        self.layout_.addWidget(self.controller, 3, 0, 2, 1)
        self.layout_.addWidget(self.progress_bar, 3, 1, 1, 3)
        self.layout_.addWidget(self.progress_display, 4, 1)
        self.layout_.addWidget(self.volume_slider, 4, 3)

    # Track manager
    @Slot(TrackManager)
    def set_manager(self, m: TrackManager):
        print(m)
        self.manager = m
        self.move_next()

    def move_next(self):
        assert self.manager is not None
        try:
            self.manager.move_next()
            self.update_text()
            if self.manager.current_song is not None:
                self.manager.current_song.ensure_audio_exists()
            if (n := self.manager.get_next()) is not None:
                n.ensure_audio_exists()

        except StopIteration:
            # we have played the last song and cannot continue
            # This should be impossible to reach
            ...

    def move_previous(self):
        assert self.manager is not None
        self.manager.move_previous()
        self.update_text()
        if self.manager.current_song is not None:
            self.manager.current_song.ensure_audio_exists()
        if (p := self.manager.get_previous()) is not None:
            p.ensure_audio_exists()

    @Slot()
    def update_text(self):
        assert self.manager is not None
        p = self.manager.get_previous()
        self.previous_label.setText(f"last: {p.data_title if p is not None else 'None'}")
        self.previous_label.setEnabled(p is not None)
        c = self.manager.current_song
        self.current_label.setText(f"now: {c.data_title  if c is not None else 'None'}")
        n = self.manager.get_next()
        self.next_label.setText(f"next: {n.data_title  if n is not None else 'None'}")
        self.next_label.setEnabled(n is not None)
        self.controller.set_enabled((p is not None, c is not None, n is not None))
        pprint([p, c, n])

    # Progress bar
    @Slot()
    def update_duration_display(self):
        self.progress_display.setText(f"{self.time}/{self.duration}")

    @Slot(int)
    def length_changed(self, duration: float):
        self.duration = timedelta(milliseconds=int(duration))
        self.progress_bar.setMaximum(int(duration))
        self.update_duration_display()

    @Slot(int)
    def progress_changed(self, progress: int):
        self.time = timedelta(milliseconds=int(progress))
        self.progress_bar.setValue(int(progress))
        self.update_duration_display()

    # Pause / Play button
    @Slot()
    def resume(self):
        self.audio_player.update_playing(True)

    @Slot()
    def pause(self):
        self.audio_player.update_playing(False)

    # Audio player
    @Slot(QMediaPlayer.MediaStatus)
    def media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.controller.set_playing(False)
            print("Player finished")


class PlayerDock(QDockWidget):
    def __init__(self, icons: Icons, fonts: Fonts, parent=None, floatable=False):
        super().__init__(parent)
        self.player = Player(icons, fonts, self)
        self.setWidget(self.player)
        self.setWindowTitle("Player controls")
        self.__empty_titlebar = QWidget()
        self.__current_titlebar = self.titleBarWidget()
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetVerticalTitleBar
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.set_floatable(floatable)

    def set_floatable(self, b: bool):
        self.setTitleBarWidget([self.__empty_titlebar, self.__current_titlebar][b])

    # @Slot(int)
    # def progress_changed(self, ms: int):
    #     """Only send progress updates when the difference is noticeable"""
    #     if (secs := ms // 1000) != self.tracked_secs:
    #         self.tracked_secs = secs
    #         self.controller.progress_changed(ms)

    def play(self, file: Path):
        print(f"Playing {file}")

    #     # Replace the media player and play it
    #     self.media_player = self.new_media_player()
    #     self.media_player.setAudioOutput(self.media_output)
    #     self.media_player.setSource(QUrl.fromLocalFile(file))
    #     self.media_player.play()
    #     self.controller.set_playing(True)

    def force_stop(self): ...

    #     if self.media_player is not None:
    #         self.media_player.stop()
    #         self.media_player.disconnect(self.media_output)
    #         self.media_player.disconnect(self.controller)
    #         del self.media_player
