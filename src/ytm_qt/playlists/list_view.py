from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
from ytm_qt.threads.download_icons import DownloadIcon

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..cache_handlers import CacheHandler


class ListView[T: QWidget](QWidget):
    request_new_icon = Signal(DownloadIcon)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.widgets: list[T] = []
        self._other_lists: list[ListView] = []
        self.cache_handler = None

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.scroll_widget = QWidget(self)
        self.box = QVBoxLayout(self.scroll_widget)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(0)
        self.scroll_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)
        self._layout.addWidget(self.scroll_area)

    def add_item(self, widget: T, idx=None):
        if idx is None:
            self.widgets.append(widget)
            self.box.addWidget(widget)
        else:
            self.widgets.insert(idx, widget)
            self.box.insertWidget(idx, widget)
        self._add_connections(widget)

    @abstractmethod
    def _add_connections(self, widget: T): ...

    def remove_item(self, item: T):
        self.widgets.remove(item)
        self.box.removeWidget(item)
        item.hide()

    def move_item(self, item: T, direction: int):
        index: int = self.box.indexOf(item)
        if index == -1 or direction == 0:
            return

        new_index = min(max(index + direction, 0), self.box.count())
        if index == new_index:
            return

        self.box.insertWidget(new_index, item)
        self.widgets.insert(new_index, self.widgets.pop(index))

    def clear(self):
        for song in self.widgets.copy():
            self.remove_item(song)

    def set_cache_handler(self, ch: CacheHandler):
        self.cache_handler = ch

    def __len__(self):
        return len(self.widgets)

    def register_other_list_views(self, lvs: Iterable[ListView]):
        self._other_lists.extend(lvs)

    def has_item(self, item: T) -> bool:
        return item in self.widgets
