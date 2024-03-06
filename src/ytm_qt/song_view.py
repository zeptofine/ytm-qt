from PySide6.QtCore import (
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .cache_handlers import CacheHandler
from .fonts import Fonts
from .icons import Icons
from .threads.download_icons import DownloadIcon
from .threads.ytdlrunner import YTMDownload, YTMExtractInfo


class SongView(QWidget):
    request_info = Signal(YTMExtractInfo)
    request_thumbnail = Signal(DownloadIcon)
    play = Signal(YTMDownload)

    def __init__(self, cache_handler: CacheHandler, icons: Icons, fonts: Fonts, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_ = QVBoxLayout(self)
        self.icons = icons
        self.fonts = fonts

        self.video_data = None
        self.cache_handler = cache_handler
        self.cache_item = None
        self.thumbnail_requested = False

        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Title", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(self.fonts.playlist_title)
        self.author_name = QLabel("Author Name", self)
        self.author_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_name.setFont(self.fonts.playlist_entry_title)

        self.play_button = QPushButton(self)
        self.play_button.setIcon(icons.play_button)
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_video)

        self.layout_.addWidget(self.thumbnail_label)
        self.layout_.addWidget(self.title_label)
        self.layout_.addWidget(self.author_name)
        self.layout_.addWidget(self.play_button)

    def play_video(self):
        assert self.video_data is not None, "Video data must be set before playing"
        request = YTMDownload(QUrl(self.video_data["original_url"]), self)
        self.play.emit(request)
