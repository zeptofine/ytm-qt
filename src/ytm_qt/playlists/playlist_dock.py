from collections.abc import Callable
from random import random

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QProgressBar,
    QToolButton,
)

from ytm_qt import CacheHandler

from .dicts import YTMSmallVideoResponse
from .playlists.list_view import ListView
from .song_widget import SongWidget
from .threads.download_icons import DownloadIcon


class PlaylistDock[T: ListView](QDockWidget):
    request_new_icon = Signal(DownloadIcon)

    def __init__(self, cache_handler: CacheHandler, playlist: T, parent=None):
        super().__init__(parent)

        self.setMinimumWidth(200)
        self.list = playlist
        self.song_requested = False
        self.cache_handler = cache_handler
        self.setWidget(self.list)

    def add_song(self, dct: YTMSmallVideoResponse):
        w = self._create_song(dct)
        self.list.add_item(w)

    def _create_song(self, dct: YTMSmallVideoResponse):
        widget = SongWidget(dct, self.cache_handler[dct["id"]], parent=self.list)
        widget.request_icon.connect(self.request_new_icon.emit)
        widget.set_icon()
        return widget

    def clear(self):
        self.list.clear()
