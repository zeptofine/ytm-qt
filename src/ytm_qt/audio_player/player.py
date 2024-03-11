import sys
from datetime import timedelta
from pathlib import Path

import yt_dlp
from PySide6.QtCore import (
    QDir,
    QRunnable,
    QSize,
    Qt,
    QThread,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QCloseEvent, QIcon, QMouseEvent
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractSlider,
    QApplication,
    QDockWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .fonts import Fonts
from .icons import Icons


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


class PlayerWidget(QWidget):
    previous_song = Signal()
    update_playing_status = Signal(bool)

    update_volume = Signal(float)

    def __init__(self, icons: Icons, fonts: Fonts, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icons = icons
        self.fonts = fonts
        self.layout_ = QGridLayout(self)

        button_size = QSize(40, 40)

        self.previous_button = QPushButton(self)
        self.previous_button.setIcon(self.icons.prev)
        self.previous_button.clicked.connect(self.previous_song.emit)
        self.play_button = QPushButton(self)
        self.play_button.setIcon(self.icons.play_button)
        self.play_button.clicked.connect(self.update_play)
        self.next_button = QPushButton(self)
        self.next_button.setIcon(self.icons.next)

        self.time = timedelta(milliseconds=0)
        self.duration = timedelta(milliseconds=0)
        self.progress_bar = TrackedSlider(Qt.Orientation.Horizontal, self)
        self.progress_bar.force_slide.connect(lambda x: print(f"Force slid: {x}"))
        self.duration_display = QLabel(self)
        self.update_duration_display()

        self.kebab = QToolButton(self)
        self.kebab.setIcon(icons.more_vert)

        self.volume_bar = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_bar.setMinimum(0)
        self.volume_bar.setMaximum(100)
        self.volume_bar.setValue(100)
        self.volume_bar.setMaximumWidth(200)
        self.volume_bar.valueChanged.connect(self._update_volume)

        self.previous_button.setFixedSize(button_size)
        self.play_button.setFixedSize(button_size)
        self.next_button.setFixedSize(button_size)

        self.layout_.addWidget(self.progress_bar, 0, 0, 1, 6)
        self.layout_.addWidget(self.previous_button, 1, 0)
        self.layout_.addWidget(self.play_button, 1, 1)
        self.layout_.addWidget(self.next_button, 1, 2)
        self.layout_.addWidget(self.duration_display, 1, 3)

        self.layout_.addWidget(self.kebab, 1, 4)
        self.layout_.addWidget(self.volume_bar, 1, 5)

        self.playing = False

    @Slot()
    def update_play(self):
        if not self.playing:
            self.playing = True
            self.play_button.setIcon(self.icons.pause_button)
            self.update_playing_status.emit(True)
        else:
            self.playing = False
            self.play_button.setIcon(self.icons.play_button)
            self.update_playing_status.emit(False)

    @Slot(bool)
    def set_playing(self, b):
        if b:
            self.playing = True
            self.play_button.setIcon(self.icons.pause_button)
        else:
            self.playing = False
            self.play_button.setIcon(self.icons.play_button)

    @Slot(int)
    def _update_volume(self, volume: int):
        self.update_volume.emit(volume / 100)

    def update_duration_display(self):
        self.duration_display.setText(f"{self.time}/{self.duration}")

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


class PlayerDock(QDockWidget):
    def __init__(self, icons: Icons, fonts: Fonts, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.fonts = fonts

        self.audio_device = QAudioDevice(QMediaDevices.defaultAudioOutput())
        self.media_output = QAudioOutput(self.audio_device, self)
        self.media_player: QMediaPlayer | None = None

        self.controller = PlayerWidget(icons, fonts, self)
        self.controller.update_playing_status.connect(self.update_playing)
        self.controller.progress_bar.force_slide.connect(self.move_position)
        self.controller.update_volume.connect(self.media_output.setVolume)
        self.tracked_secs = 0

        self.setWidget(self.controller)

    def toggle(self):
        if self.media_player is not None:
            cond = not self.media_player.isPlaying()
            self.update_playing(cond)
            self.controller.set_playing(cond)

    @Slot(bool)
    def update_playing(self, b):
        if self.media_player is not None:
            if b:
                self.media_player.play()
            else:
                self.media_player.pause()

    @Slot(int)
    def move_position(self, f: int):
        if self.media_player is not None:
            self.media_player.setPosition(int(f))

    def new_media_player(self, stop=True):
        if stop:
            self.force_stop()
        player = QMediaPlayer(self)
        player.setAudioOutput(self.media_output)
        player.durationChanged.connect(self.controller.length_changed)
        player.positionChanged.connect(self.progress_changed)
        player.playbackStateChanged.connect(self.playback_state_changed)
        player.mediaStatusChanged.connect(self.media_status_changed)
        return player

    @Slot(int)
    def progress_changed(self, ms: int):
        """Only send progress updates when the difference is noticeable"""
        if (secs := ms // 1000) != self.tracked_secs:
            self.tracked_secs = secs
            self.controller.progress_changed(ms)

    @Slot(QMediaPlayer.PlaybackState)
    def playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        ...

    @Slot(QMediaPlayer.MediaStatus)
    def media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.controller.set_playing(False)
            print("Player finished")

    def play(self, file: Path):
        # Replace the media player and play it
        self.media_player = self.new_media_player()
        self.media_player.setAudioOutput(self.media_output)
        self.media_player.setSource(QUrl.fromLocalFile(file))
        self.media_player.play()
        self.controller.set_playing(True)

    def force_stop(self):
        if self.media_player is not None:
            self.media_player.stop()
            self.media_player.disconnect(self.media_output)
            self.media_player.disconnect(self.controller)
            del self.media_player
