import math
from enum import Enum

from PySide6.QtCore import QEasingCurve, QPoint, QRect, Qt, QVariantAnimation
from PySide6.QtGui import QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QFrame, QWidget
from ytm_qt.icons import Icons


def ball_func(x: float):
    return math.sin(math.radians(x) * math.pi)


class DownloadStatus(Enum):
    NOT_DOWNLOADED = 0
    DOWNLOADING = 1
    FINISHED = 2


class DownloadProgressFrame(QFrame):
    def __init__(self, icons: Icons, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.opacity_in = QVariantAnimation(self)
        self.opacity_in.setDuration(500)
        self.opacity_in.setStartValue(0)
        self.opacity_in.setEndValue(80)
        self.opacity_in.setEasingCurve(QEasingCurve.Type.OutExpo)
        self.opacity_in.valueChanged.connect(self.set_value)
        self.opacity_out = QVariantAnimation(self)
        self.opacity_out.setDuration(500)
        self.opacity_out.setStartValue(80)
        self.opacity_out.setEndValue(0)
        self.opacity_out.setEasingCurve(QEasingCurve.Type.OutExpo)
        self.opacity_out.valueChanged.connect(self.set_value)
        self.opacity_out.finished.connect(self.fade_out_finished)
        self.opacity = 0.0

        self.checkmark_pm = icons.download_done.pixmap(512, 512)
        self.reveal_checkmark = QVariantAnimation(self)
        self.reveal_checkmark.setEasingCurve(QEasingCurve.Type.OutExpo)
        self.reveal_checkmark.setDuration(600)
        self.reveal_checkmark.setStartValue(0)
        self.reveal_checkmark.setEndValue(100)
        self.reveal_checkmark.valueChanged.connect(self.set_checkmark_visibility)
        self.reveal_checkmark.finished.connect(self.opacity_out.start)
        self.checkmark_visibility = 0.0

        self.duration = QVariantAnimation(self)
        self.duration.setDuration(2_000)
        self.duration.setStartValue(0)
        self.duration.setEndValue(100)
        self.duration.setLoopCount(-1)
        self.duration.valueChanged.connect(self.set_duration)
        self.duration_v = 0.0

        self.state = DownloadStatus.NOT_DOWNLOADED
        self.progress = 0.0

    def set_value(self, v: int):
        self.opacity = v / 100
        self.update()

    def set_checkmark_visibility(self, v: int):
        self.checkmark_visibility = v / 100
        self.update()

    def set_duration(self, v: int):
        self.duration_v = v / 100
        self.update()

    def fade_out_finished(self):
        self.checkmark_visibility = 0
        self.duration.stop()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.opacity == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.opacity)
        painter.fillRect(event.rect(), Qt.GlobalColor.black)
        if self.checkmark_visibility > 0:
            painter.drawPixmap(
                QRect(
                    0,
                    0,
                    int(self.checkmark_visibility * self.width()),
                    self.height(),
                ),
                self.checkmark_pm.copy(
                    QRect(
                        0,
                        0,
                        int(self.checkmark_pm.width() * self.checkmark_visibility),
                        self.checkmark_pm.height(),
                    )
                ),
            )
        painter.setOpacity(1 - self.checkmark_visibility)
        c = self.geometry().center()
        painter.drawEllipse(c, 10, 10)
        painter.drawArc(
            QRect(
                c.x() - 20,
                c.y() - 20,
                c.x() + 15,
                c.y() + 15,
            ),
            0,
            16 * 360,
            # int(self.progress * (16 * 360)),
        )
        f1 = ball_func(((self.duration_v - 0.1) % 1) * 360) * 3
        f2 = ball_func(self.duration_v * 360) * 3
        f3 = ball_func(((self.duration_v + 0.1) % 1) * 360) * 3

        painter.drawEllipse(QPoint(c.x() - 9, c.y() + int(f1)), 3, 3)
        painter.drawEllipse(QPoint(c.x(), c.y() + int(f2)), 3, 3)
        painter.drawEllipse(QPoint(c.x() + 9, c.y() + int(f3)), 3, 3)

    def set_status(self, status: DownloadStatus):
        self.state = status
        if status == DownloadStatus.NOT_DOWNLOADED:
            self.opacity_out.start()

        elif status == DownloadStatus.DOWNLOADING:
            self.opacity_in.start()
            self.duration.start()
        elif status == DownloadStatus.FINISHED:
            self.reveal_checkmark.start()

    def update_progress(self, progress: float, update=False):  # 0..=1
        self.progress = progress
        if update:
            self.update()
