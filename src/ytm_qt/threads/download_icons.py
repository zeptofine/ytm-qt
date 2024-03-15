import contextlib
from pathlib import Path
from queue import Empty, Queue

import requests
from PIL import Image
from PySide6.QtCore import (
    QObject,
    QRunnable,
    QThread,
    QUrl,
    Signal,
)


class DownloadIcon(QObject):
    finished = Signal()

    def __init__(self, url: QUrl, output_path: Path, small=True, parent=None):
        super().__init__(parent)
        self.url = url
        self.output_path = output_path
        self.small = small


class DownloadIconProvider(QRunnable):
    def __init__(self, q: Queue[DownloadIcon]) -> None:
        super().__init__()
        self.queue = q
        self.running = True

    def run(self):
        while self.running:
            try:
                with contextlib.suppress(Empty):
                    icon_info = self.queue.get_nowait()
                    print(f"Downloading icon at {icon_info.url.toString()} to {icon_info.output_path}")
                    data = requests.get(icon_info.url.toString())
                    if not data.ok:
                        continue
                    data.raise_for_status()
                    content = data.content
                    if not icon_info.output_path.parent.exists():
                        icon_info.output_path.parent.mkdir(parents=True)
                    with open(icon_info.output_path, "wb") as f:
                        f.write(content)

                    # Crop image to a square
                    im = Image.open(icon_info.output_path)
                    width, height = im.size
                    smaller = min(width, height)

                    left = (width - smaller) / 2
                    top = (height - smaller) / 2
                    right = (width + smaller) / 2
                    bottom = (height + smaller) / 2
                    im = im.crop((left, top, right, bottom))  # type: ignore

                    if icon_info.small and smaller > 128:
                        im = im.resize((128, 128), Image.ADAPTIVE)

                    im.save(icon_info.output_path, "PNG")
                    icon_info.finished.emit()

                    self.queue.task_done()

            except Exception as e:
                print(e)

            QThread.msleep(200)

    def stop(self):
        self.running = False
