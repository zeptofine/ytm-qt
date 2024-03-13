import sys
from collections.abc import Iterable, MutableSequence
from typing import Self

from PySide6.QtWidgets import QVBoxLayout, QWidget


class PListWidget[T: QWidget](QVBoxLayout):
    def __init__(self, widgets: list[T] | None = None, parent: QWidget | None = None):
        if parent is not None:
            super().__init__(parent=parent)
        else:
            super().__init__()
        self.parent_ = parent
        self.widgets = widgets if widgets is not None else []

    # Reversible
    def __reversed__(self):
        return self.__class__()

    # Collection
    def __contains__(self, value: object) -> bool:
        return value in self.widgets

    def __iter__(self):
        return iter(self.widgets)

    def __len__(self):
        return len(self.widgets)

    # Sequence
    def __getitem__(self, index: int) -> T:
        return self.widgets[index]

    def index(self, value: T, start: int = 0, stop: int = sys.maxsize) -> int:
        return self.widgets.index(value, start, stop)  # type: ignore

    # MutableSequence
    def __setitem__(self, index: int, value: T):
        self.widgets[index] = value
        self.takeAt(index)
        self.insertWidget(index, value)

    def __delitem__(self, index: int):
        self.removeWidget(self.widgets[index])
        del self.widgets[index]

    def insert(self, index: int, value: T):
        self.insertWidget(index, value)
        self.widgets.insert(index, value)

    def append(self, widget: T):
        self.widgets.append(widget)
        self.addWidget(widget)

    def clear(self) -> None:
        while len(self):
            self.pop(0)

    def extend(self, iterable: Iterable[T]):
        for item in iterable:
            self.append(item)

    def pop(self, index: int = -1) -> T:
        super().takeAt(index if index != -1 else len(self.widgets) - 1)
        return self.widgets.pop(index)

    def remove(self, value: T) -> None:
        self.widgets.remove(value)
        self.removeWidget(value)

    def __iadd__(self, values: Iterable) -> Self:
        for item in values:
            self.append(item)
        return self
