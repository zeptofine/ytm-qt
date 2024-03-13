from __future__ import annotations

import json
from abc import abstractmethod
from functools import partial
from typing import overload

from PySide6.QtCore import (
    QPoint,
    QPointF,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from ytm_qt import CacheHandler, Icons
from ytm_qt.dataclasses import OperationRequest, SongRequest
from ytm_qt.dicts import YTMSmallVideoResponse
from ytm_qt.song_widget import SongWidget
from ytm_qt.threads.download_icons import DownloadIcon
from ytm_qt.threads.ytdlrunner import YTMDownload

from . import operation_settings
from .plist_widget import PListWidget
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
)
from .track_manager import TrackManager


class OperationWrapper(QWidget):
    request_new_icon = Signal(DownloadIcon)
    request_song = Signal(YTMDownload)
    ungroup_signal = Signal()
    manager_generated = Signal(TrackManager)

    def __init__(self, icons: Icons, resizable=False, parent: OperationWrapper | QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        self.resizable = resizable
        self.icons = icons

        self._selected = False
        self.previous_position = None

        self.cache_handler = None
        self.widgets: PListWidget[OperationWrapper | SongWidget] = PListWidget()
        self.widgets.setContentsMargins(10, 0, 0, 0)
        self.widgets.setSpacing(0)

        self.mode: type[SongOperation] = PlayOnce
        self.mode_settings = operation_settings.get(self.mode).from_kwargs({})
        self.mode_settings_holder = QHBoxLayout()
        self.mode_settings_holder.setContentsMargins(0, 0, 0, 0)
        self.mode_settings_holder.addWidget(self.mode_settings)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.add_group_action = QAction("Add group", parent=self)
        self.add_group_action.triggered.connect(self.add_group)
        self.group_action = QAction(text="Group selected", parent=self)
        self.group_hotkey = QKeySequence(Qt.Key.Key_Control | Qt.Key.Key_G)
        self.group_action.setShortcut(self.group_hotkey)
        self.generate_action = QAction(text="Generate", parent=self)
        self.generate_action.triggered.connect(self.validate_operations)

        self.addAction(self.add_group_action)
        self.addAction(self.generate_action)

        self.modes: dict[str, tuple[QIcon, type[SongOperation]]] = {
            "Play once": (icons.play_button, PlayOnce),
            "Loop N times": (icons.repeat_one, LoopNTimes),
            "Loop": (icons.repeat_bold, LoopWholeList),
            "Random": (icons.shuffle, RandomPlay),
            "Random forever": (icons.shuffle_bold, RandomPlayForever),
        }
        self.mode_dropdown = QComboBox()
        self.mode_dropdown.currentTextChanged.connect(self.mode_changed)
        for label, (icon, _) in self.modes.items():
            self.mode_dropdown.addItem(icon, label)

        self._layout.addWidget(self.mode_dropdown, 0, 0)
        self._layout.addLayout(self.mode_settings_holder, 1, 0)

        self.tree: tuple[OperationWrapper, ...]
        if isinstance(parent, OperationWrapper):
            self.tree = (*parent.tree, self)
            self.is_suboperation = True
            ungroup_action = QAction(text="Ungroup", parent=self)
            ungroup_action.setIcon(icons.deselect)
            ungroup_action.triggered.connect(self.ungroup_self)
            self.addAction(ungroup_action)

            widget = QFrame(self)
            widget.setLayout(self.widgets)
            widget.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
            widget.setMinimumHeight(30)
            self._layout.addWidget(widget)
        else:
            self.tree = (self,)
            self.is_suboperation = False

            scroll_widget = QWidget(self)
            scroll_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
            scroll_widget.setLayout(self.widgets)
            scroll_area = QScrollArea(self)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(scroll_widget)
            self._layout.addWidget(scroll_area, 2, 0)

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
            del_action.triggered.connect(partial(self.remove_item, widget))
            widget.addAction(del_action)
            group_action = QAction(text="Group", parent=self)
            group_action.triggered.connect(partial(self.group_widget, widget))
        else:
            widget.ungroup_signal.connect(partial(self.subwidget_ungrouped, widget))

    def remove_item(self, widget: OperationWrapper | SongWidget):
        self.widgets.remove(widget)
        widget.setParent(None)
        print(f"Removed {widget}")

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
        self.widgets.clear()

    def set_cache_handler(self, ch: CacheHandler):
        self.cache_handler = ch

    def switch_mode(self, m: type[SongOperation]):
        self.mode = m

    @Slot(str)
    def mode_changed(self, t: str):
        mode = self.modes[t][1]
        self.mode = mode

        self.mode_settings_holder.removeWidget(self.mode_settings)
        self.mode_settings.deleteLater()
        # TODO: Save these after a saving system has been implemented
        #                                                             vv
        self.mode_settings = operation_settings.get(mode).from_kwargs({}, self)
        self.mode_settings_holder.addWidget(self.mode_settings)

    def ungroup_self(self):
        self.ungroup_signal.emit()

    def subwidget_ungrouped(self, w: OperationWrapper):
        idx = self.widgets.index(w)
        widgets = w.widgets
        self.remove_item(w)
        for widget in widgets:
            self.add_item(widget, idx)
            idx += 1

    def generate_operations(self) -> SongOperation:
        ops: list[SongOperation] = []
        for widget in self.widgets:
            if isinstance(widget, SongWidget):
                ops.append(SinglePlay(widget))
            else:
                ops.append(widget.generate_operations())

        return self.mode(ops, **self.mode_settings.get_kwargs())

    def validate_operations(self, ops: SongOperation | None = None):
        ops = ops or self.generate_operations()
        assert isinstance(ops, RecursiveSongOperation)
        manager = TrackManager(ops)
        self.manager_generated.emit(manager)

    @Slot()
    def add_group(self):
        assert self.cache_handler is not None
        ow = OperationWrapper(self.icons, resizable=True, parent=self)
        ow.set_cache_handler(self.cache_handler)
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
            if isinstance(item_, OperationWrapper):
                subts.append(item_)
                continue
            if item_ is item:
                return self.tree
        for wrapper in subts:
            if tree := wrapper.find_parent(item, _recursed=True):
                return tree

        return ()

    def group_widget(self, widget: SongWidget):
        # replace the widget with a OperationWrapper, then move the widget into it
        wrapper = OperationWrapper(self.icons, resizable=True, parent=self)
        idx = self.widgets.index(widget)
        self.remove_item(widget)
        wrapper.add_song(widget.request)
        self.add_item(wrapper, idx)

    def widget_clicked(self, widget: SongWidget | OperationWrapper):
        print(widget)
        # if self.first_selected is None:
        #     self.selected_widgets = [widget]
        #     self.first_selected = widget
        # elif self.first_selected is not widget.selected:
        #     mod = QApplication.keyboardModifiers()
        #     if mod & Qt.KeyboardModifier.ShiftModifier:
        #         ...
        #     else:
        #         for widget_ in self.selected_widgets:
        #             widget_.selected = False

        # widget.selected = True
        # if not widget.selected or mod & Qt.KeyboardModifier.ShiftModifier:
        #     if self.first_selected is not None and self.first_selected in self.widgets:
        #         start_idx = self.widgets.index(self.first_selected)
        #         for widget_ in self.widgets[start_idx : self.widgets.index(widget)]:
        #             widget_.selected = True
        #             self.selected_widgets.append(widget)
        #     else:
        #         for widget_ in self.selected_widgets:
        #             widget_.selected = False
        #         self.first_selected = widget
        #         widget.selected = True
        #         print("Is first selected")
        # else:
        #     ...

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

        if not mimedata.hasText():
            event.ignore()
        else:
            event.accept()

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
            item = self.create_item(SongRequest(json.loads(mimedata.text())))
            if n > len(self.widgets):
                n = None
            self.add_item(item, idx=n)

        else:
            parent = tree[-1]
            n = max(min(n, len(self.widgets) - 1), 0)
            if parent is not self:
                parent.remove_item(source)
                self.add_item(self.create_item(source.request, playable=True), n)
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
            ow = OperationWrapper(self.icons, resizable=False, parent=self)
            ow.mode = response.data_type
            for song in response.songs:
                ow.add_song(song)
            return ow

        return SongWidget(
            response.data,
            self.cache_handler[response.data["id"]],
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
