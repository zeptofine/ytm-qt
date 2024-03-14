from abc import abstractmethod
from typing import Self

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSpinBox, QWidget

from .song_ops import (
    LoopNTimes,
    SongOperation,
    Stretch,
)


class OperationSettings(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    @abstractmethod
    def get_kwargs(self) -> dict:
        return {}

    @classmethod
    @abstractmethod
    def from_kwargs(cls, dct: dict, parent=None) -> Self:
        return cls(parent)


class LNTSettings(OperationSettings):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.counter = QSpinBox(self)
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 10, 0)
        self.layout_.addWidget(self.counter)

    def get_kwargs(self):
        return {
            "times": self.counter.value(),
        }

    @classmethod
    def from_kwargs(cls, dct: dict, parent=None) -> Self:
        self = cls(parent)
        self.counter.setValue(dct.get("times", 1))
        return self


__ops: dict[type[SongOperation], type[OperationSettings]] = {
    LoopNTimes: LNTSettings,
    Stretch: LNTSettings,
}


def get(songop: type[SongOperation]) -> type[OperationSettings]:
    return __ops.get(songop, OperationSettings)
