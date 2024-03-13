from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ytm_qt import Icons


class ControlButtons(QWidget):
    back = Signal()
    pause = Signal()
    play = Signal()
    next = Signal()

    def __init__(
        self,
        icons: Icons,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.icons = icons
        self.playing = False

        self.previous_button = QPushButton(self)
        self.previous_button.setIcon(self.icons.prev)
        self.previous_button.clicked.connect(self.back)
        self.play_button = QPushButton(self)
        self.play_button.setIcon(self.icons.play_button)
        self.play_button.clicked.connect(self.play)
        self.next_button = QPushButton(self)
        self.next_button.setIcon(self.icons.next)
        self.next_button.clicked.connect(self.next)

        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(2)
        self.layout_.addWidget(self.previous_button)
        self.layout_.addWidget(self.play_button)
        self.layout_.addWidget(self.next_button)

    @Slot(bool)
    def set_playing(self, b: bool | None = None):
        self.playing = b if b is not None else not self.playing

        if self.playing:
            self.play_button.setIcon(self.icons.pause_button)
        else:
            self.play_button.setIcon(self.icons.play_button)

    def set_enabled(self, v: tuple[bool, bool, bool] | bool = True):
        if isinstance(v, bool):
            v = (v, v, v)
        self.previous_button.setEnabled(v[0])
        self.play_button.setEnabled(v[1])
        self.next_button.setEnabled(v[2])
