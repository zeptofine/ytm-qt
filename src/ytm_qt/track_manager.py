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

from .dicts import (
    YTMDownloadResponse,
    YTMPlaylistResponse,
    YTMResponse,
    YTMSearchResponse,
    YTMSmallVideoResponse,
    YTMVideoResponse,
)
from .song_ops import SongOperation, SongOperations


class TrackManager(QObject):
    def __init__(self, songops: SongOperations):
        ...
