from pathlib import Path

from PySide6.QtCore import (
    QObject,
    Qt,
    QThreadPool,
    QUrl,
    Slot,
)
from PySide6.QtWidgets import (
    QWidget,
)

from ytm_qt.playlist_generators.song_ops import RecursiveSongOperation


class TrackManager(QObject):
    def __init__(self, songops: RecursiveSongOperation): ...
