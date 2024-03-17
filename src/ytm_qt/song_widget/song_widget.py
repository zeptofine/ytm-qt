import uuid
from datetime import timedelta
from pathlib import Path
from re import L
from typing import Self

import orjson
from PySide6.QtCore import (
    QMimeData,
    QRect,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QDrag,
    QIcon,
    QMouseEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
)
from ytm_qt import CacheItem, Fonts, Icons
from ytm_qt.dataclasses import SongRequest
from ytm_qt.dicts import (
    SongMetaData,
    YTMDownloadResponse,
    YTMSmallVideoResponse,
)
from ytm_qt.song_widget.elided_text_label import ElidedTextLabel
from ytm_qt.song_widget.thumbnail_label import ThumbnailLabel
from ytm_qt.threads.download_icons import DownloadIcon
from ytm_qt.threads.ytdlrunner import YTMDownload


class SongWidget(QFrame):
    request_icon = Signal(DownloadIcon)
    request_song = Signal(YTMDownload)
    song_gathered = Signal(Path)
    play = Signal()
    clicked = Signal()

    def __init__(
        self,
        data: CacheItem,
        /,
        playable: bool = False,
        icons: Icons | None = None,
        fonts: Fonts | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.uuid = uuid.uuid4()
        self.setObjectName("SongWidget")
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)

        self._selected = False
        self.dropped_pixmap = None

        self.layout_ = QGridLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)

        self.data = data
        self.fonts = fonts or Fonts.get()
        self.icons = icons or Icons.get()

        self.thumbnail_path = data.thumbnail
        self.thumbnail_label = ThumbnailLabel(self.icons, playable, self)

        self.data_id = data.key
        if data.metadata is not None:
            self.data_title = data.metadata["title"] or "???"
            self.duration = timedelta(seconds=int(data.metadata["duration"] or -1))
            self.author = data.metadata["artist"]
            self.thumbnail = data.metadata["thumbnail"]
        else:
            self.data_title = "???"
            self.duration = timedelta(seconds=0)
            self.author = "???"
            self.thumbnail = None

        self.title_label = ElidedTextLabel(text=self.data_title, parent=self)
        self.thumbnail_requested = False
        self.title_label.setFont(self.fonts.playlist_entry_title)
        self.author_and_duration_label = QLabel(f"{self.author} - {self.duration}", parent=self)
        self.author_and_duration_label.setFont(self.fonts.playlist_entry_author)
        self.layout_.addWidget(self.thumbnail_label, 0, 0, 2, 1)
        self.layout_.addWidget(self.title_label, 0, 1)
        self.layout_.addWidget(self.author_and_duration_label, 1, 1)

        self.download_progress_frame = QFrame(self)
        self.download_progress_frame.setStyleSheet("background: rgba(0, 0, 0, 100); outline: 1px solid green")
        self.download_progress_frame.hide()

    @property
    def request(self):
        return SongRequest(self.data)

    @Slot()
    def set_icon(self):
        if self.thumbnail_path.exists():
            icon = QIcon(str(self.thumbnail_path))
            self.thumbnail_label.setPixmap(icon.pixmap(50, 50))
            self.thumbnail_requested = False
        elif (not self.thumbnail_requested) and self.thumbnail is not None:
            self.thumbnail_requested = True
            self.thumbnail_label.setPixmap(self.icons.more_horiz.pixmap(50, 50))

            self.download_task = DownloadIcon(QUrl(self.thumbnail["url"]), self.thumbnail_path)
            self.download_task.finished.connect(self.set_icon)
            self.request_icon.emit(self.download_task)

    @Slot(bool)
    def set_playing(self, b: bool = True): ...

    def start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(orjson.dumps(self.data.to_dict()).decode())
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        self.dropped_pixmap = pixmap
        self.render(pixmap)
        drag.setPixmap(pixmap)

        drag.exec(Qt.DropAction.MoveAction)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, v):
        self._selected = v
        if v:
            self.setStyleSheet("QGroupBox#SongWidget { border-color: white; }")
        else:
            self.setStyleSheet("")

    # TODO: use ✓ and ✘ or icons to represent downloaded status
    def _request_song(self):
        if self.data.metadata is not None:
            url = self.data.metadata["url"]
        else:
            url = f"https://music.youtube.com/watch?v={self.data.key}"
            print(f"Metadata is None, assuming URL is {url}")

        self.download_progress_frame.show()
        self.__update_download_geometry(0)
        request = YTMDownload(QUrl(url), parent=self)
        request.processed.connect(self._song_gathered)
        request.progress.connect(self.__download_progress)
        self.request_song.emit(request)

    def __download_progress(self, progress: dict):
        if progress["status"] == "downloading" and (total := progress.get("total_bytes")) is not None:
            self.__update_download_geometry(progress["downloaded_bytes"] / total)
        elif progress["status"] == "finished":
            self.download_progress_frame.hide()

    def __update_download_geometry(self, v: float):  # v 0..=1
        geometry = self.thumbnail_label.geometry()

        def maprange(b1, b2, s):
            # b1 + ((s - a1) * (b2 - b1) / (a2 - a1))
            return b1 + ((s - 1) * (b2 - b1) / -1)

        h = maprange(geometry.top(), geometry.bottom(), v)
        geometry = QRect(
            geometry.left(),
            geometry.top(),
            geometry.width(),
            int(h),
        )
        self.download_progress_frame.setGeometry(geometry)

    @Slot(YTMDownloadResponse)
    def _song_gathered(self, response: YTMDownloadResponse):
        download = response["requested_downloads"][0]
        path = Path(download["filepath"])
        if not self.data.audio.parent.exists():
            self.data.audio.parent.mkdir(parents=True)
        path.replace(self.data.audio)
        print(f"Moved {path} to {self.data.audio}")
        self.song_gathered.emit(self.data.audio)

    @property
    def filepath(self):
        return self.data.audio

    def ensure_audio_exists(self):
        if not self.data.audio.exists():
            print("Requesting")
            self._request_song()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:  # Dragging
            self.start_drag()

        return super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.pressed_position = event.position()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        released_position = event.position()
        if self.pressed_position == released_position:
            self.clicked.emit()
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.play.emit()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.data_id!r}, {self.data_title!r}, uuid={self.uuid!r})"
