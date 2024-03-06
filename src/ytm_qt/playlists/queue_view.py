import json
from functools import partial

from PySide6.QtCore import QPoint, QPointF, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QWidget
from ytm_qt.dicts import YTMSmallVideoResponse
from ytm_qt.dragndrop.drag_target_indicator import DragTargetIndicator

from ..song_widget import SongWidget
from .list_view import ListView


class QueueView(ListView[SongWidget]):
    play_clicked = Signal(SongWidget)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._drag_target_indicator = DragTargetIndicator(self)
        self._drag_target_indicator.hide()

    def _add_connections(self, widget: SongWidget):
        widget.play.connect(partial(self.play_song, widget))

    @Slot(SongWidget)
    def play_song(self, song: SongWidget):
        self.play_clicked.emit(song)

    # Dragging logic Modified from
    # https://www.pythonguis.com/faq/pyqt6-drag-drop-widgets/#drag-drop-widgets
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mimedata = event.mimeData()

        if not mimedata.hasText():
            event.ignore()
        else:
            event.accept()
            self._drag_target_indicator.show()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        pos = self._find_drop_position(event.position())
        w = self.box.itemAt(pos)
        if w is not None:
            self._drag_target_indicator.setGeometry(w.geometry())
        else:
            self._drag_target_indicator.setGeometry(self.scroll_area.geometry())

        event.accept()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._drag_target_indicator.hide()
        return super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._drag_target_indicator.hide()
        mimedata = event.mimeData()
        source: SongWidget = event.source()  # type: ignore

        is_foreign = True
        for lst in self._other_lists:
            if lst.has_item(source):
                break
        else:
            is_foreign = False

        n = self._find_drop_position(event.position())

        if not is_foreign:
            b = self.box.itemAt(n)
            n = min(n, len(self.widgets) - 1)
            if (b is not None and b.widget() is source) or (n >= len(self.widgets)):
                event.ignore()
                return

            self.box.insertWidget(n, source)
            try:
                self.widgets.remove(source)
                self.widgets.insert(n, source)
            except ValueError:
                print("Failed to remove and insert item to pythonic list")

        else:
            w = self.create_item(json.loads(mimedata.text()))
            if n > self.box.count():
                n = None
            self.add_item(w, idx=n)

        event.accept()

    def _find_drop_position(self, p: QPointF | QPoint) -> int:
        n = -1
        for n in range(self.box.count()):
            # Get the widget at each index in turn.
            w = self.box.itemAt(n).widget()
            if p.y() < w.geometry().center().y():
                # We didn't drag past this widget.
                # insert above it.
                break
        else:
            # We aren't below any widget,
            # so we're at the end. Increment 1 to insert after.
            n += 1
        return n

    def create_item(self, dct: YTMSmallVideoResponse):
        assert self.cache_handler is not None
        widget = SongWidget(dct, self.cache_handler[dct["id"]], parent=self)
        widget.request_icon.connect(self.request_new_icon.emit)
        widget.set_icon()
        return widget
