import contextlib
import sys
from collections import deque
from pathlib import Path
from pprint import pprint
from queue import Queue

import darkdetect as dd
import orjson
import polars as pl
from polars import DataFrame, LazyFrame
from PySide6.QtCore import (
    QEvent,
    QMimeData,
    QPoint,
    QPointF,
    Qt,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDrag,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QEnterEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
from .playlist_generators.song_ops import OperationSerializer, RecursiveOperationDict
from .playlists import PlaylistDock, PlaylistView
from .song_widget.song_widget import SongWidget
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
        self.resize(1200, 400)

        col = ("black", "white")[bool(dd.isDark())]

        self.icons = Icons.get(col)
        self.fonts = Fonts.get()

        self.header = Header(self)
        self.header.searched.connect(self.extract_url)
        self.setMenuWidget(self.header)

        self.opser: OperationSerializer[SongWidget] = OperationSerializer.default()

        self.cache_dir = Path("cache")
        self.db_path = self.cache_dir / "db.feather"
        self.cache = CacheHandler(self.cache_dir)
        self.cache.load()
        self.queue_saved_path = self.cache_dir / "queue.json"

        self.ytdlp_queue: deque[YTDLUser] = deque()
        self.ytdlp_providers = [YoutubeDLProvider(opts, self.ytdlp_queue) for _ in range(2)]
        for provider in self.ytdlp_providers:
            provider.start()

        self.icon_download_queue = Queue()
        self.icon_threadpool = QThreadPool(self)
        self.icon_providers = [DownloadIconProvider(self.icon_download_queue) for _ in range(6)]
        for provider in self.icon_providers:
            self.icon_threadpool.start(provider)

        infotask = YTMExtractInfo(URL)
        infotask.processed.connect(self.info_extracted)
        self.ytdlp_queue.append(infotask)

        self.player_dock = PlayerDock(self.icons, self.fonts, parent=self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.player_dock)

        self.play_queue_op = OperationWrapper(self.icons, self.cache, parent=self)
        self.play_queue_op.manager_generated.connect(self.player_dock.player.set_manager)
        self.player_dock.player.request_manager.connect(self.play_queue_op.validate_operations)
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

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.play_queue_dock)

        if self.queue_saved_path.exists():
            with self.queue_saved_path.open("rb") as f:
                try:
                    ops = self.opser.from_dict(
                        orjson.loads(f.read()),
                        lambda s: SongWidget(
                            self.cache[s],
                            playable=True,
                            icons=self.icons,
                            fonts=self.fonts,
                            parent=self.play_queue_op,
                        ),
                    )
                    self.play_queue_op.populate(ops)
                except Exception as e:
                    print(e)

        self.playlist_view = PlaylistView(self)
        self.playlist_view.set_cache_handler(self.cache)
        self.playlist_dock = PlaylistDock(
            cache_handler=self.cache,
            playlist=self.playlist_view,
            icons=self.icons,
            fonts=self.fonts,
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

        self.save_action = QAction(text="Save", parent=self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_queue)
        self.addAction(self.save_action)

    @Slot(str)
    def extract_url(self, url: str):
        request = YTMExtractInfo(url, parent=self)
        request.processed.connect(self.info_extracted)
        self.ytdlp_queue.append(request)

    @Slot(YTMDownload)
    def song_requested(self, request: YTMDownload):
        self.ytdlp_queue.append(request)

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

    def serialize_queue(self) -> RecursiveOperationDict:
        return self.opser.to_dict(
            self.play_queue_op.generate_operations(),
            song_serializer=lambda s: s.data_id,
        )

    def save_queue(self):
        print("Saving")
        serialized = self.serialize_queue()
        with self.queue_saved_path.open("wb") as f:
            f.write(orjson.dumps(serialized))

    def load_queue(self): ...

    def closeEvent(self, event: QCloseEvent) -> None:
        with contextlib.suppress(Exception):
            self.player_dock.force_stop()

            df = pl.from_dicts([{"key": k, **v} for k, v in self.cache.generate_dict()])
            print(df)
            self.cache.save()
            df.write_ipc(self.db_path)

            for provider in self.ytdlp_providers:
                provider.stop()
                provider.wait(10_000)
                provider.terminate()

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
