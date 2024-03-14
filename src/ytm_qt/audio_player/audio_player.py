from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaPlayer


class AudioPlayer(QObject):
    duration_changed = Signal(int)
    progress_changed = Signal(int)
    playback_changed = Signal(QMediaPlayer.PlaybackState)
    mediastatus_changed = Signal(QMediaPlayer.MediaStatus)

    def __init__(self, audio_device: QAudioDevice, parent=None):
        super().__init__(parent)
        self.audio_device = audio_device
        self.media_output = QAudioOutput(self.audio_device, self)
        self.media_player: QMediaPlayer | None = None

    def new_audio_device(self, audio_device: QAudioDevice):
        self.audio_device = audio_device
        self.media_output = QAudioOutput(self.audio_device, self)
        if self.media_player is not None:
            self.media_player.setAudioOutput(self.media_output)

    def new_media_player(self, stop=True):
        if stop:
            self.force_stop()
        player = QMediaPlayer(self)
        player.setAudioOutput(self.media_output)
        player.durationChanged.connect(self.duration_changed.emit)
        player.positionChanged.connect(self.progress_changed.emit)
        player.playbackStateChanged.connect(self.playback_changed.emit)
        player.mediaStatusChanged.connect(self.mediastatus_changed.emit)
        return player

    def force_stop(self):
        if self.media_player is not None:
            self.media_player.stop()
            self.media_player.disconnect(self.media_output)
            del self.media_player

    def change_position(self, v: int):
        if self.media_player is not None:
            self.media_player.setPosition(v)

    def play(self, p: Path):
        self.media_player = self.new_media_player()
        self.media_player.setSource(QUrl.fromLocalFile(p))
        self.media_player.play()

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
