from __future__ import annotations

from abc import abstractmethod
from functools import partial
from pprint import pprint
from typing import Self, overload

import orjson
from PySide6.QtCore import (
    QEvent,
    QMimeData,
    QPoint,
    QPointF,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QDrag,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QEnterEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from ytm_qt import CacheHandler, Icons
from ytm_qt.operation_dataclasses import OperationRequest, SongRequest
from ytm_qt.song_widget.song_widget import SongWidget
from ytm_qt.threads.download_icons import DownloadIcon
from ytm_qt.threads.ytdlrunner import YTMDownload

from . import operation_settings
from .plist_widget import PListLayout
from .song_ops import (
    InfiniteLoopType,
    LoopNTimes,
    LoopWholeList,
    PlayOnce,
    RandomPlay,
    RandomPlayForever,
    RecursiveSongOperation,
    SinglePlay,
    SongOperation,
    get_mode_icons,
)
from .track_manager import TrackManager


class OperationWrapper(QWidget):
    request_new_icon = Signal(DownloadIcon)
    request_song = Signal(YTMDownload)
    ungroup_signal = Signal()
    manager_generated = Signal(TrackManager)

    def __init__(
        self,
        icons: Icons,
        cache_handler: CacheHandler,
        parent: OperationWrapper | QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        self.icons = icons

        self._selected = False
        self.previous_position = None

        self.cache_handler = cache_handler
        self.widgets: PListLayout[OperationWrapper | SongWidget] = PListLayout()
        self.widgets.setContentsMargins(0, 0, 0, 0)
        self.widgets.setSpacing(0)

        self.mode: type[RecursiveSongOperation[SongWidget]] = PlayOnce
        self.mode_settings = operation_settings.get(self.mode).from_kwargs({})
        self.mode_settings_holder = QHBoxLayout()
        self.mode_settings_holder.setContentsMargins(0, 0, 0, 0)
        self.mode_settings_holder.addWidget(self.mode_settings)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.download_all = QAction("Download all", parent=self)
        self.download_all.triggered.connect(self.download_all_)
        self.add_group_action = QAction("Add group", parent=self)
        self.add_group_action.triggered.connect(self.add_group)
        self.group_action = QAction(text="Group selected", parent=self)
        self.group_hotkey = QKeySequence(Qt.Key.Key_Control | Qt.Key.Key_G)
        self.group_action.setShortcut(self.group_hotkey)
        self.generate_action = QAction(text="Generate", parent=self)
        self.generate_action.triggered.connect(self.validate_operations)
        self.clear_action = QAction(text="Clear", parent=self)
        self.clear_action.triggered.connect(self.clear)

        self.addAction(self.download_all)
        self.addAction(self.add_group_action)
        self.addAction(self.generate_action)
        self.addAction(self.clear_action)

        self.modes = get_mode_icons(icons)
        self._mode_keys = {k.key(): k for k in self.modes}

        self.mode_dropdown = QComboBox()
        self.mode_dropdown.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.mode_dropdown.currentTextChanged.connect(self.change_mode)
        for operation, icon in self.modes.items():
            self.mode_dropdown.addItem(icon, operation.key())

        self._layout.addWidget(self.mode_dropdown, 0, 0, 1, 1)
        self._layout.addLayout(self.mode_settings_holder, 0, 1)

        self.tree: tuple[OperationWrapper, ...]
        if isinstance(parent, OperationWrapper):
            self.tree = (*parent.tree, self)
            self.is_suboperation = True
            ungroup_action = QAction(text="Ungroup", parent=self)
            ungroup_action.setIcon(icons.deselect)
            ungroup_action.triggered.connect(self.ungroup_self)
            self.addAction(ungroup_action)

            widget = QWidget(self)
            widget.setLayout(self.widgets)
            widget.setContentsMargins(5, 0, 0, 0)
            widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
            widget.setMinimumWidth(300)
            self._layout.addWidget(widget, 1, 0, 1, 2)
        else:
            self.tree = (self,)
            self.is_suboperation = False

            scroll_widget = QWidget(self)
            scroll_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
            scroll_widget.setLayout(self.widgets)

            scroll_area = QScrollArea(self)
            # scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(scroll_widget)
            self._layout.addWidget(scroll_area, 1, 0, 1, 2)

    @Slot(str)
    def change_mode(self, t: str, kwargs: dict | None = None):
        kwargs = kwargs if kwargs is not None else {}
        mode = self._mode_keys[t]
        self.mode = mode

        # TODO: Save these after a saving system has been implemented
        #                                                             vv
        new_mode_settings = operation_settings.get(mode)
        if new_mode_settings is not type(self.mode_settings):  # intentionally subclass non-inclusive
            self.mode_settings.deleteLater()
            self.mode_settings = new_mode_settings.from_kwargs(kwargs, self)
            self.mode_settings_holder.removeWidget(self.mode_settings)
            self.mode_settings_holder.addWidget(self.mode_settings)

        if self.mode_dropdown.currentText() != t:
            self.mode_dropdown.setCurrentText(t)

    def add_item(self, widget: OperationWrapper | SongWidget, idx=None):
        if idx is None:
            self.widgets.append(widget)
        else:
            self.widgets.insert(idx, widget)
        self._add_connections(widget)

    @abstractmethod
    def _add_connections(self, widget: OperationWrapper | SongWidget):
        if isinstance(widget, SongWidget):
            widget.request_icon.connect(self.request_new_icon)
            widget.request_song.connect(self.request_song)
            widget.set_icon()
            widget.clicked.connect(partial(self.widget_clicked, widget))
            del_action = QAction(text="Delete", parent=self)
            del_action.triggered.connect(partial(self.delete_item, widget))
            widget.addAction(del_action)
            group_action = QAction(text="Group", parent=self)
            group_action.triggered.connect(partial(self.group_widget, widget))
        else:
            widget.ungroup_signal.connect(partial(self.subwidget_ungrouped, widget))
            widget.request_song.connect(self.request_song)
            widget.request_new_icon.connect(self.request_new_icon)

    def delete_item(self, widget: OperationWrapper | SongWidget):
        self.widgets.remove(widget)
        widget.setParent(None)

        print(f"Removed {widget}")
        widget.destroy()

    def move_item(self, item: OperationWrapper | SongWidget, direction: int):
        """Moves an item in the box to a new position.
        Requires the object to be in the current box.

        Args:
            item (OperationWrapper | SongWidget): The item to move
            direction (int): The direction of the move (ex. 1 for forward, -1 for backward)
        """
        index: int = self.widgets.index(item)
        if index == -1 or direction == 0:
            return

        new_index = min(max(index + direction, 0), len(self.widgets))
        if index == new_index:
            return

        self.widgets.insert(new_index, self.widgets.pop(index))

    def clear(self):
        for widget in self.widgets:
            widget.setParent(None)
            widget.destroy()
        self.widgets.clear()

    def ungroup_self(self):
        self.ungroup_signal.emit()

    def subwidget_ungrouped(self, w: OperationWrapper):
        idx = self.widgets.index(w)
        widgets = w.widgets
        self.delete_item(w)
        for widget in widgets:
            self.add_item(widget, idx)
            idx += 1

    def generate_operations(self) -> RecursiveSongOperation[SongWidget]:
        ops: list[SongOperation] = []
        for widget in self.widgets:
            if isinstance(widget, SongWidget):
                ops.append(SinglePlay(widget))
            else:
                ops.append(widget.generate_operations())

        return self.mode(ops, **self.mode_settings.get_kwargs())

    @classmethod
    def from_operations(
        cls,
        sop: RecursiveSongOperation[SongWidget],
        cache_handler: CacheHandler,
        icons: Icons,
        parent=None,
    ) -> Self:
        self = cls(icons, cache_handler, parent)
        self.change_mode(sop.key(), kwargs=sop.get_kwargs())
        self.populate(sop)
        return self

    def populate(self, sop: RecursiveSongOperation[SongWidget]):
        for op in sop.songs:
            if isinstance(op, SinglePlay):
                self.add_item(op.song)
            elif isinstance(op, RecursiveSongOperation):
                self.add_item(self.from_operations(op, cache_handler=self.cache_handler, icons=self.icons, parent=self))

    def validate_operations(self, ops: SongOperation | None = None):
        ops = ops or self.generate_operations()
        assert isinstance(ops, RecursiveSongOperation)

        manager = TrackManager(ops.simplify())
        self.manager_generated.emit(manager)

    @Slot()
    def download_all_(self):
        for song in self.widgets:
            if isinstance(song, OperationWrapper):
                song.download_all_()
            else:
                song.ensure_audio_exists()

    @Slot()
    def add_group(self):
        assert self.cache_handler is not None
        ow = OperationWrapper(self.icons, cache_handler=self.cache_handler, parent=self)
        self.add_item(ow)

    @Slot()
    def group_selected(self): ...

    def __len__(self):
        return len(self.widgets)

    def find_parent(self, item: SongWidget | OperationWrapper, _recursed=False) -> tuple[OperationWrapper, ...]:
        """This method checks if the given item exists in the widgets of the entire tree.
        It iterates over the widgets, adding any OperationWrapper instances to a list.
        If the item matches any widget, it returns the tree of the current object.
        If no match is found in the widgets, it iterates over the OperationWrapper instances,
        checking if the item exists in any of them.

        Args:
            item (SongWidget | OperationWrapper): The item to be searched in the widgets.

        Returns:
            tuple[OperationWrapper, ...]: The tree where the item is found. If item is not found, returns an empty tuple.
        Note:
            This method might be infinite loop unsafe, as it recursively checks for the item in OperationWrapper instances.
        """
        if len(self.tree) > 1 and not _recursed:
            return self.tree[0].find_parent(item)
        subts: list[OperationWrapper] = []
        for item_ in self.widgets:
            if item_ is item:
                return self.tree
            if isinstance(item_, OperationWrapper):
                subts.append(item_)
        for wrapper in subts:
            if tree := wrapper.find_parent(item, _recursed=True):
                return tree

        return ()

    def group_widget(self, widget: SongWidget):
        # replace the widget with a OperationWrapper, then move the widget into it
        wrapper = OperationWrapper(self.icons, self.cache_handler, parent=self)
        idx = self.widgets.index(widget)
        self.delete_item(widget)
        wrapper.add_song(widget.request)
        self.add_item(wrapper, idx)

    def widget_clicked(self, widget: SongWidget | OperationWrapper):
        print(widget)
        # Tell the controller to skip to this widget

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, v):
        self._selected = v
        if v:
            self.setStyleSheet("QGroupBox#SongWidget { border-color: white; }")
        else:
            self.setStyleSheet("")

    # Dragging logic Modified from
    # https://www.pythonguis.com/faq/pyqt6-drag-drop-widgets/#drag-drop-widgets
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mimedata = event.mimeData()

        if not mimedata.hasText() or event.source() is self:
            event.ignore()
        else:
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_suboperation:  # Dragging
            self.start_drag()

        return super().mouseMoveEvent(event)

    def start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText("OperationWrapper")
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        self.dropped_pixmap = pixmap
        self.render(pixmap)
        drag.setPixmap(pixmap)

        drag.exec(Qt.DropAction.MoveAction)

    @property
    def request(self) -> OperationRequest:
        return OperationRequest(
            self.mode,
            self.mode_settings.get_kwargs(),
            [song.request for song in self.widgets],
        )

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.accept()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        mimedata = event.mimeData()
        source: SongWidget | OperationWrapper = event.source()  # type: ignore
        tree = self.find_parent(source)

        n = self._find_drop_position(event.position())
        if not tree:  # tree must be ()
            assert self.cache_handler is not None
            js = orjson.loads(mimedata.text())
            citem = self.cache_handler(js["key"], js)
            item = self.create_item(SongRequest(citem))
            if n > len(self.widgets):
                n = None
            self.add_item(item, idx=n)

        else:
            parent = tree[-1]
            n = max(min(n, len(self.widgets) - 1), 0)
            if parent is not self:
                request = source.request
                if isinstance(source, OperationWrapper):
                    source.clear()
                    source.ungroup_signal.emit()
                else:
                    parent.delete_item(source)

                self.add_item(self.create_item(request, playable=True), n)

                # parent.widgets.remove(source)
                # self.widgets.insert(n, source)
            else:
                self.widgets.widgets.remove(source)
                self.widgets.insert(n, source)

        event.accept()

    @overload
    def create_item(self, response: SongRequest, playable=True) -> SongWidget: ...

    @overload
    def create_item(self, response: OperationRequest, playable=True) -> OperationWrapper: ...

    def create_item(self, response: SongRequest | OperationRequest, playable=True) -> SongWidget | OperationWrapper:
        assert self.cache_handler is not None
        if isinstance(response, OperationRequest):
            ow = OperationWrapper(self.icons, self.cache_handler, parent=self)
            ow.change_mode(response.data_type.key(), kwargs=response.data_config)

            for song in response.songs:
                ow.add_song(song)
            return ow

        item = self.cache_handler[response.data.key]

        return SongWidget(
            item,
            icons=self.icons,
            playable=playable,
            parent=self.tree[0],
        )

    def add_song(self, response: SongRequest | OperationRequest):
        item = self.create_item(response)
        self.add_item(item)

    def _find_drop_position(self, p: QPointF | QPoint) -> int:
        n = -1
        for n in range(len(self.widgets)):
            # Get the widget at each index in turn.
            w = self.widgets[n]
            if p.y() <= w.geometry().center().y():
                # We didn't drag past this widget.
                # insert above it.
                break
        else:
            # We aren't below any widget,
            # so we're at the end. Increment 1 to insert after.
            n += 1
        return n

    def __repr__(self):
        return f"{self.__class__.__name__}({self.widgets}, {self.mode})"
