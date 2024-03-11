from PySide6.QtCore import (
    QObject,
)

from ytm_qt.song_widget import SongWidget

from .song_ops import InfiniteLoopType, RecursiveSongOperation


class TrackManager(QObject):
    def __init__(self, songops: RecursiveSongOperation, parent=None):
        super().__init__(parent)
        self.songops = songops
        self.__generator = songops.get()
        self.song_buffer = []
        self.current_song: SongWidget | None = None
        self.current_index = -1

    def move_next(self) -> SongWidget:
        self.current_index += 1
        if len(self.song_buffer) == self.current_index:
            ni = self.__add_to_buffer()
        else:
            ni = self.song_buffer[self.current_index]
        self.current_song = ni
        return ni

    def move_previous(self):
        assert len(self.song_buffer) > 0
        self.current_index = max(self.current_index - 1, 0)
        self.current_song = self.song_buffer[self.current_index]
        return self.current_song

    def get_next(self) -> SongWidget | None:
        if len(self.song_buffer) == self.current_index + 1:
            print("Next item has yet to be generated, generating now")
            try:
                return self.__add_to_buffer()
            except StopIteration:
                return None
        else:
            return self.song_buffer[self.current_index + 1]

    def get_previous(self) -> SongWidget | None:
        if self.current_index <= 0:
            return None
        return self.song_buffer[self.current_index - 1]

    def __add_to_buffer(self):
        ni = next(self.__generator)
        self.song_buffer.append(ni)
        return ni

    def skip_until(self, song: SongWidget, timeout=-1):
        if self.songops.is_infinite() != InfiniteLoopType.NONE and timeout == -1:
            raise NotImplementedError("Infinite loops not implemented for skip_until")

        while timeout > 0 or timeout == -1:
            try:
                n = self.move_next()
                if n == song:
                    return
                timeout -= 1
            except StopIteration:
                break

    def __repr__(self):
        return f"{self.__class__.__name__}({self.songops})"
