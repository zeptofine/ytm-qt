import json
import random
from collections.abc import Sequence
from datetime import timedelta
from functools import partial
from pprint import pprint

from PySide6.QtCore import (
    Property,
    QEvent,
    QMimeData,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRunnable,
    QSize,
    Qt,
    QThread,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
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
    QPaintEvent,
    QPixmap,
)
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .cache_handlers import CacheItem
from .dicts import (
    SongMetaData,
    YTMSmallVideoResponse,
    YTMVideoResponse,
)
from .fonts import Fonts
from .icons import Icons
from .threads.download_icons import DownloadIcon


class ElidedTextLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text_: str = text
        self.metrics = QFontMetrics(self.font())

    def setFont(self, arg__1: QFont | str | Sequence[str]) -> None:
        super().setFont(arg__1)
        self.metrics = QFontMetrics(self.font())

    def set_text(self, text):
        self.text_ = text
        super().setText(text)

    def updateElidedText(self):
        width = self.width()
        elided_text = self.metrics.elidedText(self.text_, Qt.TextElideMode.ElideRight, width)
        self.setText(elided_text)

    def resizeEvent(self, event):
        self.updateElidedText()


HighlightStyle = """
QLabel {
    background-color: rgba(0, 0, 0, 50);
    outline: 10px solid white;
}
"""


class ThumbnailLabel(QWidget):
    clicked = Signal()

    def __init__(self, icons: Icons, playable: bool, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFixedSize(50, 50)

        self.icons = icons
        self.label = QLabel(self)
        self.label.setFixedSize(50, 50)
        self.playable = playable
        if playable:
            self.highlighted_label = QLabel(self)
            self.highlighted_label.setPixmap(icons.play_button.pixmap(20, 20))
            self.highlighted_label.setStyleSheet(HighlightStyle)
            self.highlighted_label.setMinimumSize(self.size())
            self.highlighted_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.highlighted_label.setLineWidth(10)
            self.highlighted_label.hide()

    def setPixmap(self, pixmap: QPixmap):
        self.label.setPixmap(pixmap)

    def enterEvent(self, event: QEnterEvent) -> None:
        if self.playable:
            self.highlighted_label.show()
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        if self.playable:
            self.highlighted_label.hide()
        return super().leaveEvent(event)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        self.clicked.emit()
        return super().mousePressEvent(ev)


class SongWidget(QGroupBox):
    request_icon = Signal(DownloadIcon)
    play = Signal()
    clicked = Signal()

    def __init__(
        self,
        data: YTMSmallVideoResponse,
        cache: CacheItem,
        /,
        playable: bool = False,
        white_icons: Icons | None = None,
        fonts: Fonts | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("SongWidget")
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.setMinimumHeight(50)
        self.setContentsMargins(0, 0, 0, 0)

        self._selected = False

        self.layout_ = QGridLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.data_ = data
        self.cache = cache
        self.fonts = fonts or Fonts.get()
        self.icons = white_icons or Icons.get("white")

        self.thumbnail_path = cache.thumbnail
        self.thumbnail_label = ThumbnailLabel(self.icons, playable, self)

        self.data_title = self.data_["title"]
        self.title_label = ElidedTextLabel(text=self.data_title, parent=self)
        self.thumbnail_requested = False
        self.title_label.setFont(self.fonts.playlist_entry_title)
        self.duration = timedelta(seconds=int(self.data_["duration"]))
        self.author_and_duration_label = QLabel(f"{self.data_["channel"]} - {self.duration}", parent=self)
        self.author_and_duration_label.setFont(self.fonts.playlist_entry_author)
        self.layout_.addWidget(self.thumbnail_label, 0, 0, 2, 1)
        self.layout_.addWidget(self.title_label, 0, 1)
        self.layout_.addWidget(self.author_and_duration_label, 1, 1)

        self.thumbnail = max(
            self.data_["thumbnails"],
            key=lambda d: (
                d.get("height"),
                d.get("width"),
                d.get("preference"),
            ),
        )

    @classmethod
    def from_dct(cls, dct: YTMSmallVideoResponse, cache: CacheItem, parent=None):
        return cls(dct, cache, parent=parent)

    @Slot()
    def set_icon(self):
        if self.thumbnail_path.exists():
            icon = QIcon(str(self.thumbnail_path))
            self.thumbnail_label.setPixmap(icon.pixmap(50, 50))
            self.thumbnail_requested = False
        elif not self.thumbnail_requested:
            self.thumbnail_requested = True
            self.download_task = DownloadIcon(QUrl(self.thumbnail["url"]), self.thumbnail_path)
            self.download_task.finished.connect(self.set_icon)
            self.request_icon.emit(self.download_task)

    @Slot(bool)
    def set_playing(self, b: bool = True): ...

    def start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(json.dumps(self.data_))
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
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
        return f"{self.__class__.__name__}({self.data_title!r})"
