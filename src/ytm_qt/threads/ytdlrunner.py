import uuid
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
from yt_dlp.utils import DownloadError
from ytm_qt.dicts import (
    YTMDownloadResponse,
    YTMResponse,
)


class YTDLUser(QObject):
    error = Signal(Exception)
    started = Signal()
    finished = Signal()
    progress = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    def key(self):
        return str(uuid.uuid1())

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

    def key(self):
        return self.url

    def process(self, ytdl: YoutubeDL) -> None:
        try:
            info = ytdl.extract_info(self.url, download=False, process=self.do_process)
        except DownloadError as e:
            self.error.emit(e)
        if info is None:
            self.error.emit(Exception("Info is None"))
        else:
            self.processed.emit(info)


class YTMDownload(YTDLUser):
    processed = Signal(YTMDownloadResponse)

    def __init__(self, url: QUrl, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def key(self):
        return self.url

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

            QThread.msleep(250)  # sleep for 250 ms to avoid busy waiting

    def stop(self):
        self.running = False
