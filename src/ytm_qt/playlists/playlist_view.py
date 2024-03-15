from functools import partial

from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
)
from PySide6.QtWidgets import (
    QWidget,
)

from ..song_widget import SongWidget
from .list_view import ListView


class PlaylistView(ListView[SongWidget]):
    add_to_queue = Signal(SongWidget)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.now_playing_widget: SongWidget | None = None

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.add_to_queue_action = QAction(text="Add all to queue", parent=self)
        self.add_to_queue_action.triggered.connect(self._add_all_to_queue)
        self.addAction(self.add_to_queue_action)

    def _add_connections(self, widget: SongWidget):
        widget.play.connect(partial(self._song_clicked, widget))

    def _add_all_to_queue(self):
        for song in self.widgets:
            self.add_to_queue.emit(song)

    @Slot(SongWidget)
    def _song_clicked(self, song: SongWidget):
        self.add_to_queue.emit(song)
