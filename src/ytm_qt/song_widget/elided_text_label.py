from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QLabel


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
