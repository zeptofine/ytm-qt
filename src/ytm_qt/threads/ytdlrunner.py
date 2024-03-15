from abc import abstractmethod
from collections import deque
from collections.abc import Callable
from pprint import pprint

from PySide6.QtCore import (
    QObject,
    QThread,
    QUrl,
    Signal,
)
from yt_dlp import YoutubeDL
from ytm_qt.dicts import (
    YTMDownloadResponse,
    YTMResponse,
)


class YTDLUser(QObject):
    error = Signal(str)
    started = Signal()
    finished = Signal()
    progress = Signal(dict)

    def __init__(self, hook: Callable[[dict], None] | None = None, parent=None):
        super().__init__(parent)
        self.hook = hook

    def run(self, ytdl: YoutubeDL):
        self.started.emit()
        self.process(ytdl)
        self.finished.emit()

    @abstractmethod
    def process(self, ytdl: YoutubeDL): ...


class YTMExtractInfo(YTDLUser):
    processed = Signal(YTMResponse)

    def __init__(self, url: str, process=False, parent=None) -> None:
        super().__init__(parent)
        self.url = url
        self.do_process = process

    def process(self, ytdl: YoutubeDL) -> None:
        info = ytdl.extract_info(self.url, download=False, process=self.do_process)

        if info is None:
            self.error.emit("Failed to extract info")
        else:
            self.processed.emit(info)


class YTMDownload(YTDLUser):
    processed = Signal(YTMDownloadResponse)

    def __init__(self, url: QUrl, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def process(self, ytdl: YoutubeDL) -> None:
        info = ytdl.extract_info(self.url.toString(), download=True)

        if info is None:
            self.error.emit("Failed to extract info")
        else:
            self.processed.emit(info)


class YoutubeDLProvider(QThread):
    err = Signal(Exception)

    def __init__(self, opts: dict, q: deque[YTDLUser]) -> None:
        super().__init__()
        self.opts = opts
        self.queue = q
        self.running = True

    def run(self):
        while self.running:
            try:
                user = self.queue.popleft()
                try:
                    with YoutubeDL(
                        {
                            "progress_hooks": [user.progress.emit],
                            **self.opts,
                        }
                    ) as ytdl:
                        user.run(ytdl)
                except Exception as e:
                    self.err.emit(e)
            except IndexError:
                pass

    def stop(self):
        self.running = False
