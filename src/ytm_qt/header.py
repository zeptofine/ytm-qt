from urllib.parse import quote

import validators
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget


class Header(QWidget):
    searched = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(40)

        self.layout_ = QHBoxLayout(self)
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search / URL...")
        self.search_bar.returnPressed.connect(self._searched)
        self.layout_.addWidget(self.search_bar)

    @Slot()
    def _searched(self):
        if t := self.search_bar.text():
            if validators.url(t.strip()):
                self.searched.emit(t)
            else:
                query = quote(t)
                search_url = f"https://music.youtube.com/search?q={query}"
                self.searched.emit(search_url)
