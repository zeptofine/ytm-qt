import contextlib
import sys
from pathlib import Path
from queue import Queue

import darkdetect as dd
from PySide6.QtCore import (
    Qt,
    QThreadPool,
    QUrl,
    Slot,
)
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QWidget,
)

from .audio_player import PlayerDock
from .cache_handlers import CacheHandler
from .dicts import (
    YTMDownloadResponse,
    YTMPlaylistResponse,
    YTMResponse,
    YTMSearchResponse,
    YTMSmallVideoResponse,
    YTMVideoResponse,
)
from .enums import ResponseTypes
from .fonts import Fonts
from .header import Header
from .icons import Icons
from .playlist_generators.op_wrapper import OperationWrapper
from .playlists import PlaylistDock, PlaylistView
from .song_widget import SongWidget
from .threads.download_icons import DownloadIconProvider
from .threads.ytdlrunner import YoutubeDLProvider, YTDLUser, YTMDownload, YTMExtractInfo

URL = r"https://music.youtube.com/playlist?list=PLu_TDFCG1ZjxzrBAAULOOQrr-6sgf4da8"

# video:    https://music.youtube.com/watch?v=zfa9l2GYkRI&si=zVWB-BVlzl9K8USd
# playlist: https://music.youtube.com/playlist?list=PLu_TDFCG1ZjxzrBAAULOOQrr-6sgf4da8
# search:   https://music.youtube.com/search?q=hurry+hurry


opts = {
    "check_formats": "selected",
    "extract_flat": "discard_in_playlist",
    "format": "bestaudio/best",
    "fragment_retries": 10,
    "ignoreerrors": "only_download",
    "outtmpl": {"default": "cache/%(id)s"},
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredquality": "5",
        },
        {
            "key": "FFmpegConcat",
            "only_multi_video": True,
            "when": "playlist",
        },
    ],
    "retries": 10,
}


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ytm-qt")
        self.resize(1200, 800)

        col = ("black", "white")[bool(dd.isDark())]

        self.icons = Icons.get(col)
        self.fonts = Fonts.get()

        self.header = Header(self)
        self.header.searched.connect(self.extract_url)
        self.setMenuWidget(self.header)

        self.cache_dir = Path("cache")
        self.cache = CacheHandler(self.cache_dir)
        self.cache.load()

        self.ytdlp_queue: Queue[YTDLUser] = Queue()
        self.ytdlp_thread = YoutubeDLProvider(opts, self.ytdlp_queue)
        self.ytdlp_thread.start()

        self.icon_download_queue = Queue()
        self.icon_threadpool = QThreadPool(self)
        self.icon_providers = [DownloadIconProvider(self.icon_download_queue) for _ in range(4)]
        for provider in self.icon_providers:
            self.icon_threadpool.start(provider)

        infotask = YTMExtractInfo(URL)
        infotask.processed.connect(self.info_extracted)
        self.ytdlp_queue.put(infotask)

        self.player_dock = PlayerDock(self.icons, self.fonts, parent=self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.player_dock)

        self.play_queue_op = OperationWrapper(self.icons, parent=self)
        self.play_queue_op.set_cache_handler(self.cache)
        self.play_queue_op.manager_generated.connect(self.player_dock.player.set_manager)
        self.play_queue_op.request_song.connect(self.song_requested)
        self.play_queue_dock = QDockWidget()
        self.play_queue_dock.setWidget(self.play_queue_op)
        self.play_queue_dock.setMinimumWidth(400)
        self.play_queue_dock.setAllowedAreas(
            Qt.DockWidgetArea.NoDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.play_queue_dock.setWindowTitle("Playing queue")

        # self.play_queue_op
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.play_queue_dock)

        self.playlist_view = PlaylistView(self)
        self.playlist_view.set_cache_handler(self.cache)
        self.playlist_dock = PlaylistDock(
            cache_handler=self.cache,
            playlist=self.playlist_view,
            parent=self,
        )
        self.playlist_view.add_to_queue.connect(self.playlist_song_clicked)
        self.playlist_dock.setMinimumWidth(300)
        self.playlist_dock.request_new_icon.connect(self.icon_download_queue.put)
        self.playlist_dock.setAllowedAreas(
            Qt.DockWidgetArea.NoDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.playlist_dock.setWindowTitle("Playlist view")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.playlist_dock)

        self.main_w = QWidget()
        self.setCentralWidget(self.main_w)

    @Slot(str)
    def extract_url(self, url: str):
        request = YTMExtractInfo(url, parent=self)
        request.processed.connect(self.info_extracted)
        self.ytdlp_queue.put(request)

    @Slot(YTMDownload)
    def song_requested(self, request: YTMDownload):
        print(f"Request recieved: {request}")
        self.ytdlp_queue.put(request)

    @Slot(SongWidget)
    def playlist_song_clicked(self, song: SongWidget):
        self.play_queue_op.add_song(song.request)

    @Slot(YTMResponse)
    def info_extracted(self, info: YTMResponse):
        response_type = ResponseTypes.from_extractor_key(info["extractor_key"])
        print("Estimated response type: ", response_type)
        match response_type:
            case ResponseTypes.VIDEO:
                _video: YTMVideoResponse = info  # type: ignore

            case ResponseTypes.PLAYLIST:
                playlist: YTMPlaylistResponse = info  # type: ignore
                self.playlist_dock.clear()
                for entry in playlist["entries"]:
                    self.playlist_dock.add_song(entry)

            case ResponseTypes.SEARCH:
                _search: YTMSearchResponse = info  # type: ignore

    def closeEvent(self, event: QCloseEvent) -> None:
        with contextlib.suppress(Exception):
            self.player_dock.force_stop()

            self.cache.save()
            self.ytdlp_thread.stop()
            self.ytdlp_thread.wait(10_000)
            self.ytdlp_thread.terminate()
            for provider in self.icon_providers:
                provider.stop()

        return super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
