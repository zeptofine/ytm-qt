from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PySide6.QtGui import QFont

FONTS_PATH = Path(__file__).parent


@dataclass
class Fonts:
    playlist_title: QFont
    playlist_entry_title: QFont
    playlist_entry_author: QFont
    playlist_entry_duration: QFont

    @classmethod
    @cache
    def get(cls):
        playlist_title = QFont("Arial", 16)
        playlist_entry_title = QFont("Arial", 12)
        playlist_entry_author = QFont("Arial", 10)
        playlist_entry_duration = QFont("Arial", 8)

        return cls(
            playlist_title=playlist_title,
            playlist_entry_title=playlist_entry_title,
            playlist_entry_author=playlist_entry_author,
            playlist_entry_duration=playlist_entry_duration,
        )
