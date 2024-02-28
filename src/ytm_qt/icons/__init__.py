from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PySide6.QtGui import QIcon

ICONS_PATH = Path(__file__).parent


@dataclass
class Icons:
    play_button: QIcon
    pause_button: QIcon
    more_horiz: QIcon
    more_vert: QIcon
    next: QIcon
    prev: QIcon
    repeat: QIcon
    repeat_bold: QIcon
    repeat_one: QIcon
    shuffle: QIcon
    shuffle_bold: QIcon

    @classmethod
    @cache
    def get(cls):
        return cls(
            play_button=QIcon(str(ICONS_PATH / "google" / "play_arrow.svg")),
            pause_button=QIcon(str(ICONS_PATH / "google" / "pause.svg")),
            more_horiz=QIcon(str(ICONS_PATH / "google" / "more_horiz.svg")),
            more_vert=QIcon(str(ICONS_PATH / "google" / "more_vert.svg")),
            next=QIcon(str(ICONS_PATH / "google" / "last_page.svg")),
            prev=QIcon(str(ICONS_PATH / "google" / "first_page.svg")),
            repeat=QIcon(str(ICONS_PATH / "google" / "repeat_FILL1_wght400.svg")),
            repeat_bold=QIcon(str(ICONS_PATH / "google" / "repeat_FILL1_wght700.svg")),
            repeat_one=QIcon(str(ICONS_PATH / "google" / "repeat_one_FILL1_wght700.svg")),
            shuffle=QIcon(str(ICONS_PATH / "google" / "shuffle_FILL1_wght400.svg")),
            shuffle_bold=QIcon(str(ICONS_PATH / "google" / "shuffle_FILL1_wght700.svg")),
        )
