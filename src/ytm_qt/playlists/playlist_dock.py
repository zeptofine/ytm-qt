from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDockWidget,
)

from ytm_qt import CacheHandler, CacheItem, Fonts
from ytm_qt.dicts import YTMSmallVideoResponse
from ytm_qt.icons import Icons
from ytm_qt.song_widget.song_widget import SongWidget
from ytm_qt.threads.download_icons import DownloadIcon

from .list_view import ListView


class PlaylistDock[T: ListView](QDockWidget):
    request_new_icon = Signal(DownloadIcon)

    def __init__(self, cache_handler: CacheHandler, playlist: T, icons: Icons, fonts: Fonts, parent=None):
        super().__init__(parent)

        self.setMinimumWidth(200)
        self.list = playlist
        self.song_requested = False
        self.cache_handler = cache_handler
        self.icons = icons
        self.setWidget(self.list)

    def add_song(self, dct: YTMSmallVideoResponse):
        w = self._create_song(dct)
        self.list.add_item(w)

    def _create_song(self, dct: YTMSmallVideoResponse):
        widget = SongWidget(
            CacheItem.from_ytmsvr(dct, self.cache_handler),
            playable=False,
            icons=self.icons,
            parent=self.list,
        )
        widget.request_icon.connect(self.request_new_icon)
        widget.set_icon()
        return widget

    def clear(self):
        self.list.clear()
