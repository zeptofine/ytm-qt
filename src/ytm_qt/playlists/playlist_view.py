from functools import partial

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget

from ..song_widget import SongWidget
from .list_view import ListView


class PlaylistView(ListView[SongWidget]):
    song_clicked = Signal(SongWidget)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.now_playing_widget: SongWidget | None = None

    def _add_connections(self, widget: SongWidget):
        widget.play.connect(partial(self._song_clicked, widget))

    @Slot(SongWidget)
    def _song_clicked(self, song: SongWidget):
        self.song_clicked.emit(song)

    def set_playing(self, idx: int):
        if self.now_playing_widget is not None:
            self.now_playing_widget.set_playing(False)
        w = self.widgets[idx]
        w.set_playing()
        self.now_playing_widget = w
        print(f"Playing {idx} ({w})")

    def set_playing_widget(self, w: SongWidget):
        return self.set_playing(self.widgets.index(w))
