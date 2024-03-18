import sys
from datetime import timedelta
from pathlib import Path
from pprint import pprint

from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QResizeEvent
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
    QScrollArea,
    QSizePolicy,
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
    STYLE = """
QSlider::groove:horizontal {
    margin: 5px 0;
    border-radius: 1px;
}
QSlider::groove:horizontal:hover {
    margin: 2px 0;
}

QSlider::handle:horizontal {
    background: white;
    width: 5px;
    height: 2px;
    border-radius: 5px;
}


QSlider::add-page:horizontal {
    background: black;
    margin: 4px 0;
    border-radius: 1px;
}


QSlider::sub-page:horizontal {
    background: white;
    margin: 4px 0;
    border-radius: 1px;
}

"""
    force_slide = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setStyleSheet(self.STYLE)
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
        self.controller.play.connect(self.toggle_playing)
        self.controller.pause.connect(self.pause)
        self.controller.back.connect(self.move_previous)

        self.time = timedelta(milliseconds=0)
        self.duration = timedelta(milliseconds=0)
        self.progress_bar = TrackedSlider(self)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.force_slide.connect(self.change_position)
        self.progress_display = QLabel(self)
        self.progress_display.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.update_duration_display()

        self.manager = None
        self.audio_player = AudioPlayer(QMediaDevices.defaultAudioOutput())  # TODO: Make this configurable
        self.audio_player.duration_changed.connect(self.duration_changed)
        self.audio_player.progress_changed.connect(self.progress_changed)
        self.audio_player.progress_changed.connect(self.update_duration_display)
        self.audio_player.mediastatus_changed.connect(self.media_status_changed)
        self.audio_player.playback_changed.connect(self.playbackstate_changed)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.volume_slider.setMinimumWidth(150)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setMinimum(0)
        self.volume_slider.valueChanged.connect(lambda v: self.audio_player.media_output.setVolume(v / 100))
        self.volume_slider.setValue(100)
        self.previous_label = QLabel(self)
        self.current_label = QLabel(self)
        self.next_label = QLabel(self)

        self.sublayout = QGridLayout()
        self.sublayout.setContentsMargins(2, 2, 2, 2)
        self.sublayout.setSpacing(2)
        self.sublayout.addWidget(self.previous_label, 0, 0, 1, 3)
        self.sublayout.addWidget(self.current_label, 1, 0, 1, 3)
        self.sublayout.addWidget(self.next_label, 2, 0, 1, 3)
        self.sublayout.addWidget(self.controller, 4, 0, 1, 1)
        self.sublayout.addWidget(self.progress_display, 4, 1)
        self.sublayout.addWidget(self.volume_slider, 4, 3)

        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        self.layout_.addWidget(self.progress_bar)
        self.layout_.addLayout(self.sublayout)

    # Track manager
    @Slot(TrackManager)
    def set_manager(self, m: TrackManager):
        print(m)
        self.manager = m
        self.move_next()

    def try_play(self):
        if self.manager is not None and self.manager.current_song is not None:
            if self.manager.current_song.filepath.exists():
                self.play(self.manager.current_song.filepath)
            else:
                self.manager.current_song.song_gathered.connect(self.play)
                self.manager.current_song.ensure_audio_exists()

    def move_next(self):
        assert self.manager is not None
        try:
            self.manager.move_next()
            self.update_text()
            self.try_play()
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
        self.try_play()
        if (p := self.manager.get_previous()) is not None:
            p.ensure_audio_exists()

    @Slot(Path)
    def play(self, p: Path):
        if (
            self.manager is not None
            and self.manager.current_song is not None
            and self.manager.current_song.filepath == p
        ):
            self.audio_player.play(p)

    @Slot()
    def update_text(self):
        assert self.manager is not None
        p = self.manager.get_previous()
        c = self.manager.current_song
        n = self.manager.get_next()
        use_p = p is not None
        use_c = c is not None
        use_n = n is not None
        self.previous_label.setText(f"last: {p.data_title if use_p else 'None'}")
        self.previous_label.setEnabled(use_p)
        self.current_label.setText(f"now: {c.data_title  if use_c else 'None'}")
        self.next_label.setText(f"next: {n.data_title  if use_n else 'None'}")
        self.next_label.setEnabled(use_n)
        self.controller.set_enabled((use_p, use_c, use_n))

    # Progress bar
    @Slot()
    def update_duration_display(self):
        self.progress_display.setText(f"{self.time}/{self.duration}")

    @Slot(int)
    def duration_changed(self, duration: float):
        self.duration = timedelta(milliseconds=int(duration))
        self.progress_bar.setMaximum(int(duration))
        self.update_duration_display()

    @Slot(int)
    def change_position(self, position: int):
        print(f"Force slid: {position}")
        self.audio_player.change_position(position)

    @Slot(int)
    def progress_changed(self, progress: int):
        self.time = timedelta(milliseconds=int(progress))
        self.progress_bar.setValue(int(progress))
        self.update_duration_display()

    # Pause / Play button
    @Slot()
    def resume(self):
        self.audio_player.update_playing(True)
        self.controller.set_playing(True)

    @Slot()
    def pause(self):
        self.audio_player.update_playing(False)
        self.controller.set_playing(False)

    @Slot()
    def toggle_playing(self):
        if (
            self.audio_player.media_player is None
            or self.audio_player.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState
        ):
            self.resume()
        else:
            self.pause()

    # Audio player
    @Slot(QMediaPlayer.MediaStatus)
    def media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.controller.set_playing(False)
            print("Player finished")

    @Slot(QMediaPlayer.PlaybackState)
    def playbackstate_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.controller.set_playing(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.controller.set_playing(False)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            ...


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
