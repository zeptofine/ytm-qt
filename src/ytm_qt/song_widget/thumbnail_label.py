from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel, QWidget
from ytm_qt import Icons

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
