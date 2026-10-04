#!/usr/bin/env python3
r"""
Foto Nxënësit - helper for photographing students for school badges.

How it works
  1. Asks for the school name and creates  Documents\<school>  (reuses it if it exists).
  2. Type a student's full name and press Enter. After you confirm that the portrait
     was taken, the name is added to the current class list and the field is cleared.
  3. "Përfundo klasën" asks for the class name (X-1, X-2 ...) and the ordering
     (Albanian alphabet or photographing order), then writes
     Documents\<school>\<class>\<class>.txt  as a numbered list with the date and time
     each portrait was confirmed, followed by the class total, and clears the list
     for the next class.
  4. "Përfundo shkollën" goes back to the start screen for the next school.

The first time each new version of the .exe starts, it runs its own tests (the tests
folder is packed inside) in a window before opening. From source, run it with
"--kontrollo" to see that window.

Build a single .exe on Windows (in the folder that contains this file):
  py -m pip install --upgrade -r requirements.txt
  py -m PyInstaller --noconfirm --clean --onefile --windowed --name FotoNxenesit --collect-data customtkinter --add-data "tests;tests" foto_nxenesit.py
The program is then  dist\FotoNxenesit.exe
"""

from __future__ import annotations

import contextlib
import io
import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

import customtkinter as ctk

# ------------------------------------------------------------------ settings
APP_NAME = "Foto Nxënësit"
APP_VERSION = "1.3.2"
TXT_ENCODING = "utf-8-sig"  # UTF-8 with BOM: ë and ç show correctly in Notepad, Word and Excel
AUTO_CAPITALIZE = True      # "arta krasniqi" is saved as "Arta Krasniqi"
DRAFT_FILE = "_klasa e papërfunduar.txt"  # autosave of the class in progress, inside the school folder
STAMP_FORMAT = "%d.%m.%Y %H:%M:%S"  # date and time each portrait was confirmed, as written in class files

# ------------------------------------------------------------------ look
PAPER = "#ECF0F5"       # window background
SHEET = "#FFFFFF"       # list sheet, dialogs, input fields
INK = "#24369B"         # ballpoint blue: main actions and accents
INK_HOVER = "#1B2878"
INK_TINT = "#DDE3F6"    # selected row, hover of outlined buttons
TEXT = "#161E36"
GRAPHITE = "#5D6980"    # secondary text
RULE = "#D2D9E3"        # hairlines and borders
ROW_ALT = "#F5F7FB"     # every second row of the list
GREEN = "#13805B"       # "photo taken", "save class"
GREEN_HOVER = "#0D6647"
RED = "#B8352A"
RED_HOVER = "#962A21"
RED_TINT = "#F6E3E1"
AMBER = "#95600A"
OVERLAY = "#D3DAE4"     # behind dialogs
SLOT = "#E6EBF1"        # empty photo on the badge preview
SILHOUETTE = "#C0C9D6"
FIGURE_SPACE = "\u2007"  # as wide as a digit: keeps the list numbers aligned

if sys.platform.startswith("win"):
    UI_FONT, UI_FONT_STRONG, STRONG_WEIGHT = "Segoe UI", "Segoe UI Semibold", "normal"
else:  # other systems are only used for testing
    UI_FONT, UI_FONT_STRONG, STRONG_WEIGHT = "DejaVu Sans", "DejaVu Sans", "bold"

BUTTON_STYLES = {
    "ink": dict(fg_color=INK, hover_color=INK_HOVER, text_color="#FFFFFF"),
    "green": dict(fg_color=GREEN, hover_color=GREEN_HOVER, text_color="#FFFFFF"),
    "red": dict(fg_color=RED, hover_color=RED_HOVER, text_color="#FFFFFF"),
    "plain": dict(fg_color="transparent", hover_color=INK_TINT, text_color=INK,
                  border_width=2, border_color=INK),
    "plain-red": dict(fg_color="transparent", hover_color=RED_TINT, text_color=RED,
                      border_width=2, border_color=RED),
}
STATUS_COLORS = {"ok": GREEN, "warn": AMBER, "error": RED, "info": GRAPHITE}


# ------------------------------------------------------------------ Albanian alphabetical order
ALBANIAN_ALPHABET = (
    "a", "b", "c", "ç", "d", "dh", "e", "ë", "f", "g", "gj", "h", "i", "j", "k", "l", "ll", "m",
    "n", "nj", "o", "p", "q", "r", "rr", "s", "sh", "t", "th", "u", "v", "x", "xh", "y", "z", "zh",
)
_RANK = {letter: (i + 1) * 10 for i, letter in enumerate(ALBANIAN_ALPHABET)}
_RANK["w"] = _RANK["v"] + 5  # W is not an Albanian letter; it goes between V and X
_DIGRAPHS = frozenset(letter for letter in ALBANIAN_ALPHABET if len(letter) == 2)
_NO_DECOMPOSITION = {"đ": "d", "ı": "i", "ł": "l", "ø": "o", "ß": "s", "æ": "a", "œ": "o"}
_WORD = re.compile(r"[^\W\d_]+")


def _foreign_letter_rank(ch: str) -> int:
    """Letters from other languages (č, ć, š, ž, é, ü ...) go right after their base letter."""
    base = unicodedata.normalize("NFD", ch)[0]
    base = _NO_DECOMPOSITION.get(base, base)
    return _RANK[base] + 1 if base in _RANK else 1000 + ord(ch)


def _word_key(word: str) -> tuple:
    key, i = [], 0
    while i < len(word):
        pair = word[i:i + 2]
        if pair in _DIGRAPHS:  # dh, gj, ll, nj, rr, sh, th, xh, zh count as one letter
            key.append(_RANK[pair])
            i += 2
        else:
            ch = word[i]
            key.append(_RANK[ch] if ch in _RANK else _foreign_letter_rank(ch))
            i += 1
    return tuple(key)


def albanian_sort_key(name: str):
    """Sort key following A B C Ç D Dh E Ë F G Gj H I J K L Ll M N Nj O P Q R Rr S Sh T Th U V X Xh Y Z Zh.
    Names are compared word by word, so "Ana Zeka" comes before "Anabela Berisha"."""
    text = unicodedata.normalize("NFC", unicodedata.normalize("NFC", name).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return tuple(_word_key(word) for word in _WORD.findall(text)), text, name


def sort_albanian(names: list[str]) -> list[str]:
    return sorted(names, key=albanian_sort_key)


# ------------------------------------------------------------------ names, folders, files
def clean_name(raw: str) -> str:
    """Trim, collapse repeated spaces and capitalise the first letter of each part of the name."""
    name = " ".join(unicodedata.normalize("NFC", raw).split())
    if AUTO_CAPITALIZE:
        name = "".join(ch.upper() if ch.isalpha() and (i == 0 or name[i - 1] in " -") else ch
                       for i, ch in enumerate(name))
    return name


def same_name(name: str) -> str:
    """Comparison form of a name: ignores upper/lower case and extra spaces."""
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


def count_names(n: int) -> str:
    return "1 emër" if n == 1 else f"{n} emra"


_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def folder_name(raw: str) -> str:
    """Turn what was typed into a valid Windows folder name.
    Quotes become “ ”, / \\ : become -, and < > | ? * are dropped."""
    out, opening = [], True
    for ch in unicodedata.normalize("NFC", raw):
        if ch == '"':
            out.append("“" if opening else "”")
            opening = not opening
        elif ch in "/\\:":
            out.append("-")
        elif ch in "<>|?*" or ord(ch) < 32:
            continue
        else:
            out.append(ch)
    name = " ".join("".join(out).split()).rstrip(". ")  # Windows drops trailing dots and spaces
    if name.split(".")[0].strip().upper() in _RESERVED:
        name = "_" + name
    return name[:100].rstrip(". ")


def documents_dir() -> Path:
    """The user's real Documents folder (also when OneDrive has moved it)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:  # CSIDL_PERSONAL
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Documents"


@dataclass
class Student:
    name: str
    taken: datetime | None = None  # when the portrait was confirmed


TOTAL_PREFIX = "Gjithsej:"
_NUMBERED = re.compile(r"^\d+\s*[.)]\s*(.+)$")
_STAMPED = re.compile(r"^(.+?)\s+[–-]\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2}(?::\d{2})?)$")


def format_line(number: int, student: Student) -> str:
    """One line of a class file:  12. Arta Krasniqi – 01.10.2026 09:42:17"""
    line = f"{number}. {student.name}"
    if student.taken is not None:
        line += f" – {student.taken.strftime(STAMP_FORMAT)}"
    return line


def numbered_lines(students: list[Student]) -> list[str]:
    return [format_line(i, student) for i, student in enumerate(students, 1)]


def class_file_lines(students: list[Student], class_name: str) -> list[str]:
    return numbered_lines(students) + ["", f"{TOTAL_PREFIX} {len(students)} nxënës në klasën {class_name}"]


def _parse_stamp(day: str, clock: str) -> datetime | None:
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(f"{day} {clock}", fmt)
        except ValueError:
            continue
    return None


def parse_students(text: str) -> list[Student]:
    """Read a class list written by any version of the program (or edited by hand).
    Numbers, dates and the total line are recognised, so only the students remain."""
    students = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(TOTAL_PREFIX):
            continue
        numbered = _NUMBERED.match(line)
        if numbered:
            line = numbered.group(1).strip()
        taken = None
        stamped = _STAMPED.match(line)
        if stamped:
            taken = _parse_stamp(stamped.group(2), stamped.group(3))
            if taken is not None:
                line = stamped.group(1).strip()
        students.append(Student(line, taken))
    return students


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def read_students(path: Path) -> list[Student]:
    return parse_students(read_text(path))


def count_names_in(path: Path) -> int:
    try:
        return len(read_students(path)) if path.is_file() else 0
    except OSError:
        return 0


def write_lines(path: Path, lines: list[str]) -> None:
    """Write the lines with Windows line endings. A temporary file is renamed over the old one,
    so an existing list is never left half-written."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding=TXT_ENCODING, newline="\r\n") as f:
            f.write("\n".join(lines))
        for attempt in range(8):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:  # e.g. antivirus is scanning the file for a moment
                if attempt == 7:
                    raise
                time.sleep(0.15)
    finally:
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()


def save_class(school_dir: Path, class_folder: str, students: list[Student],
               alphabetical: bool, merge: bool) -> tuple[Path, list[Student], list[Student]]:
    """Create <school>/<class>/<class>.txt. With merge=True the new students are added to the ones
    already in the file (names already there are skipped). Returns (file, saved list, skipped)."""
    class_dir = school_dir / class_folder
    class_dir.mkdir(parents=True, exist_ok=True)
    txt = class_dir / f"{class_folder}.txt"
    final, skipped = list(students), []
    if merge and txt.is_file():
        final = read_students(txt)
        known = {same_name(s.name) for s in final}
        for student in students:
            if same_name(student.name) in known:
                skipped.append(student)
            else:
                final.append(student)
    if alphabetical:
        final = sorted(final, key=lambda s: albanian_sort_key(s.name))
    write_lines(txt, class_file_lines(final, class_folder))
    return txt, final, skipped


def count_saved_classes(school_dir: Path) -> int:
    return school_summary(school_dir)[0]


def school_summary(school_dir: Path) -> tuple[int, int]:
    """How many classes are saved in the school folder, and how many students they hold."""
    classes = students = 0
    try:
        folders = [d for d in school_dir.iterdir() if d.is_dir()]
    except OSError:
        return 0, 0
    for folder in folders:
        txt = folder / f"{folder.name}.txt"
        if txt.is_file():
            classes += 1
            students += count_names_in(txt)
    return classes, students


def list_time(taken: datetime | None, today: date | None = None) -> str:
    """How a photo time is shown in the app: only the time for today, date and time otherwise."""
    if taken is None:
        return ""
    if taken.date() == (today or date.today()):
        return taken.strftime("%H:%M:%S")
    return taken.strftime("%d.%m. %H:%M:%S")


def open_folder(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # noqa: S606 - opens the folder in File Explorer
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ------------------------------------------------------------------ self-check on the first start of a version
CHECK_RECORD = "kontrolli.txt"          # the version that last passed the self-check
CHECK_REPORT = "kontrolli-raporti.txt"  # written when a check fails


def app_data_dir() -> Path:
    """Documents\\FotoNxenesit: the program's own small files (the self-check record and report)."""
    return documents_dir() / "FotoNxenesit"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def tests_dir() -> Path:
    """The tests folder: packed inside the .exe, or next to this file when run from source."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "tests"


def checked_version(folder: Path | None = None) -> str:
    try:
        return ((folder or app_data_dir()) / CHECK_RECORD).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def remember_checked_version(folder: Path | None = None) -> None:
    folder = folder or app_data_dir()
    with contextlib.suppress(OSError):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / CHECK_RECORD).write_text(APP_VERSION, encoding="utf-8")


def check_needed(force: bool = False, folder: Path | None = None, frozen: bool | None = None) -> bool:
    """True on the first start of each new version of the .exe (or when asked with --kontrollo)."""
    if force:
        return True
    if not (is_frozen() if frozen is None else frozen):
        return False  # from source, the tests are run with pytest instead
    return checked_version(folder) != APP_VERSION


@dataclass
class CheckResult:
    total: int
    failed: list[str]
    report: str
    exit_code: int

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and self.total > 0 and not self.failed


def run_self_check(folder: Path, on_progress=None) -> CheckResult:
    """Run the tests in `folder` with pytest. on_progress(done, total) is called as they finish."""
    import pytest

    main_module = sys.modules.get("__main__")
    if "foto_nxenesit" not in sys.modules and getattr(main_module, "APP_NAME", None) == APP_NAME:
        sys.modules["foto_nxenesit"] = main_module  # the tests import the running program by name

    class Progress:
        def __init__(self):
            self.total = self.done = 0
            self.failed: list[str] = []

        def pytest_collection_finish(self, session):
            self.total = len(session.items)
            if on_progress:
                on_progress(0, self.total)

        def pytest_runtest_logreport(self, report):
            if report.failed and report.nodeid not in self.failed:
                self.failed.append(report.nodeid)
            if report.when == "teardown":
                self.done += 1
                if on_progress:
                    on_progress(self.done, self.total)

    progress, output = Progress(), io.StringIO()
    autoload = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = pytest.main([str(folder), "-q", "-p", "no:cacheprovider", "-p", "no:faulthandler",
                                "--capture=sys"], plugins=[progress])
    finally:
        if autoload is None:
            os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
        else:
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = autoload
    return CheckResult(progress.total, progress.failed, output.getvalue(), int(code))


# ------------------------------------------------------------------ dialogs
class Modal:
    """A dialog drawn inside the main window. It cannot get lost behind the window, and
    Enter / Esc always reach it. run() waits until a button is chosen and returns its key."""

    def __init__(self, app: App, title: str, buttons: list[tuple[str, str, str]],
                 default: str, cancel: str, width: int = 520):
        self.app = app
        self.default, self.cancel = default, cancel
        self.width = width
        self.validate = None      # optional: function(key) -> error text or None
        self.focus_widget = None  # optional: widget that gets the keyboard focus
        self.actions = {}         # optional: key -> function that runs without closing the dialog
        self.result = None
        self._done = tk.BooleanVar(master=app, value=False)
        self._opened_at = 0.0
        self._error_shown = False

        self.overlay = ctk.CTkFrame(app, fg_color=OVERLAY, corner_radius=0)
        card = ctk.CTkFrame(self.overlay, fg_color=SHEET, corner_radius=16, border_width=1, border_color=RULE)
        card.place(relx=0.5, rely=0.5, anchor="center")
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(padx=32, pady=(24, 28))
        ctk.CTkFrame(box, fg_color="transparent", width=width, height=1).pack()  # sets the dialog width
        app.label(box, title, size=22, strong=True, wrap=width).pack(fill="x")
        self.body = ctk.CTkFrame(box, fg_color="transparent")
        self.body.pack(fill="x")
        self.error = app.label(box, "", size=14, color=RED, wrap=width)
        self.buttons = ctk.CTkFrame(box, fg_color="transparent")
        self.buttons.pack(fill="x", pady=(24, 0))
        for col, (key, caption, style) in enumerate(buttons):
            self.buttons.grid_columnconfigure(col, weight=1, uniform="modal")
            app.button(self.buttons, caption, style, lambda k=key: self.choose(k), height=50, size=16).grid(
                row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == len(buttons) - 1 else 6))

    def add_text(self, text: str, color: str = GRAPHITE, size: int = 15, strong: bool = False,
                 pady=(10, 0)) -> ctk.CTkLabel:
        label = self.app.label(self.body, text, size=size, color=color, strong=strong, wrap=self.width)
        label.pack(fill="x", pady=pady)
        return label

    def add_badge(self, school: str, name: str, caption: str) -> None:
        """Preview of the student's badge: school, photo slot with viewfinder corners, name."""
        app = self.app
        badge = ctk.CTkFrame(self.body, fg_color=SHEET, corner_radius=12, border_width=2, border_color=RULE)
        badge.pack(fill="x", pady=(16, 0))
        inner = ctk.CTkFrame(badge, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=(14, 18))
        app.label(inner, school, size=13, strong=True, color=INK, wrap=self.width - 60).pack(fill="x")
        app.rule(inner, INK, 2).pack(fill="x", pady=(6, 14))
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        scale = ctk.ScalingTracker.get_widget_scaling(app)
        w, h = round(84 * scale), round(104 * scale)
        photo = tk.Canvas(row, width=w, height=h, bg=SLOT, highlightthickness=0, bd=0)
        photo.pack(side="left")
        photo.create_oval(round(w * .33), round(h * .20), round(w * .67), round(h * .50), fill=SILHOUETTE, outline="")
        photo.create_oval(round(w * .12), round(h * .57), round(w * .88), round(h * 1.25), fill=SILHOUETTE, outline="")
        m, arm, thick = round(7 * scale), round(15 * scale), max(2, round(2.5 * scale))
        for x, y, dx, dy in ((m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
            photo.create_line(x, y + dy * arm, x, y, x + dx * arm, y, fill=GREEN, width=thick)

        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=(20, 0))
        app.label(text, name, size=26, strong=True, wrap=self.width - 170).pack(fill="x")
        app.label(text, caption, size=14, color=GRAPHITE).pack(fill="x", pady=(2, 0))

    def show_error(self, text: str) -> None:
        self.error.configure(text=text)
        if not self._error_shown:
            self.error.pack(fill="x", pady=(14, 0), before=self.buttons)
            self._error_shown = True

    def clear_error(self) -> None:
        if self._error_shown:
            self.error.pack_forget()
            self._error_shown = False

    def watch(self, field: ctk.CTkEntry, on_change=None) -> None:
        """Hide the error as soon as the text in the field changes (not on the Enter key itself)."""
        last = {"text": field.get()}

        def changed(_event=None):
            if field.get() != last["text"]:
                last["text"] = field.get()
                self.clear_error()
                if on_change:
                    on_change()

        field.bind("<KeyRelease>", changed)

    def choose(self, key: str) -> None:
        if self.result is not None:
            return
        if key in self.actions:
            self.actions[key]()
            return
        if key != self.cancel and self.validate is not None:
            problem = self.validate(key)
            if problem:
                self.show_error(problem)
                return
        self.result = key
        self._done.set(True)

    def press_default(self) -> None:
        # ignore an Enter that arrives right as the dialog opens (key bounce / double press)
        if time.monotonic() - self._opened_at >= 0.25:
            self.choose(self.default)

    def press_cancel(self) -> None:
        self.choose(self.cancel)

    def run(self) -> str:
        app = self.app
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.lift()
        app.modal = self
        app.update_idletasks()
        (self.focus_widget or self.overlay).focus_set()
        self._opened_at = time.monotonic()
        try:
            app.wait_variable(self._done)
        finally:
            app.modal = None
            self.overlay.destroy()
        return self.result


# ------------------------------------------------------------------ main window
class App(ctk.CTk):
    def __init__(self, force_check: bool = False):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=PAPER)
        self.title(f"{APP_NAME} {APP_VERSION}")
        self._fonts: dict = {}
        self.modal: Modal | None = None
        self.screen = "school"
        self.documents = documents_dir()
        self.school_dir: Path | None = None
        self.students: list[Student] = []
        self.sort_choice = "alpha"
        self.draft_ok = True
        self.scale = ctk.ScalingTracker.get_widget_scaling(self)
        # plain Tk widgets are not scaled by customtkinter, so their fonts are sized in pixels here
        self.list_font = tkfont.Font(self, family=UI_FONT, size=-round(18 * self.scale))
        self.list_head_font = tkfont.Font(self, family=UI_FONT_STRONG, size=-round(13 * self.scale),
                                          weight=STRONG_WEIGHT)

        self._fit_window()
        self._style_table()
        self._build_school_screen()
        self._build_class_screen()
        self._build_check_screen()
        self._check_default = None
        if check_needed(force_check):
            self._show_screen("check")
            self.after(300, self._start_check)
        else:
            self._show_screen("school")

        for sequence in ("<Return>", "<KP_Enter>"):
            self.bind(sequence, self._on_enter)
        self.bind("<Escape>", self._on_escape)
        self.bind("<Tab>", lambda e: "break" if self.modal else None)
        self.bind("<Key>", self._on_key)
        for key, letter in (("e", "ë"), ("E", "Ë"), ("c", "ç"), ("C", "Ç")):
            self.bind(f"<Alt-{key}>", lambda e, letter=letter: self._type_letter(letter))
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(150, self.focus_input)

    # ---------------------------------------------------------------- small builders
    def font(self, size: int, strong: bool = False) -> ctk.CTkFont:
        key = (size, strong)
        if key not in self._fonts:
            self._fonts[key] = ctk.CTkFont(family=UI_FONT_STRONG if strong else UI_FONT, size=size,
                                           weight=STRONG_WEIGHT if strong else "normal")
        return self._fonts[key]

    def label(self, parent, text: str, size: int = 15, color: str = TEXT, strong: bool = False,
              wrap: int = 0, anchor: str = "w", justify: str = "left") -> ctk.CTkLabel:
        return ctk.CTkLabel(parent, text=text, font=self.font(size, strong), text_color=color,
                            wraplength=wrap, anchor=anchor, justify=justify)

    def button(self, parent, text: str, style: str, command, height: int = 48, size: int = 16,
               width: int = 140) -> ctk.CTkButton:
        return ctk.CTkButton(parent, text=text, command=command, height=height, width=width, corner_radius=8,
                             font=self.font(size, strong=True), **BUTTON_STYLES[style])

    def entry(self, parent, height: int, size: int, border: str = INK) -> ctk.CTkEntry:
        return ctk.CTkEntry(parent, height=height, font=self.font(size), corner_radius=8, border_width=2,
                            border_color=border, fg_color=SHEET, text_color=TEXT)

    def rule(self, parent, color: str = RULE, height: int = 1) -> tk.Frame:
        return tk.Frame(parent, bg=color, height=max(1, round(height * self.scale)), bd=0, highlightthickness=0)

    def _letter_row(self, parent, field: ctk.CTkEntry) -> ctk.CTkFrame:
        """ë and ç buttons for keyboards that don't have those keys."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        for letter in ("ë", "ç"):
            ctk.CTkButton(row, text=letter, width=48, height=36, corner_radius=8, font=self.font(18, strong=True),
                          command=lambda letter=letter: self._type_into(field, letter),
                          **BUTTON_STYLES["plain"]).pack(side="left", padx=(0, 8))
        self.label(row, "ose Alt+E dhe Alt+C", size=13, color=GRAPHITE).pack(side="left", padx=(4, 0))
        return row

    def _fit_window(self) -> None:
        scale = ctk.ScalingTracker.get_window_scaling(self)
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(1100, int(screen_w / scale * 0.92))
        h = min(740, int(screen_h / scale * 0.86))
        x = max(0, int((screen_w - w * scale) / 2))
        y = max(0, int((screen_h - h * scale) / 2.4))
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min(860, w), min(560, h))

    def _style_table(self) -> None:
        s = self.scale
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Klasa.Treeview", background=SHEET, fieldbackground=SHEET, foreground=TEXT,
                        font=self.list_font, rowheight=round(34 * s), borderwidth=0, relief="flat")
        style.map("Klasa.Treeview", background=[("selected", INK_TINT)], foreground=[("selected", TEXT)])
        style.layout("Klasa.Treeview", [("Klasa.Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Klasa.Treeview.Heading", background=SHEET, foreground=GRAPHITE, font=self.list_head_font,
                        relief="flat", borderwidth=0, bordercolor=SHEET, lightcolor=SHEET, darkcolor=SHEET,
                        padding=(round(4 * s), round(8 * s)))
        style.map("Klasa.Treeview.Heading", background=[("active", SHEET), ("pressed", SHEET)],
                  relief=[("active", "flat"), ("pressed", "flat")])

    # ---------------------------------------------------------------- self-check screen
    def _build_check_screen(self) -> None:
        screen = self.check_screen = ctk.CTkFrame(self, fg_color=PAPER, corner_radius=0)
        col = ctk.CTkFrame(screen, fg_color="transparent")
        col.place(relx=0.5, rely=0.45, anchor="center")
        width = 540
        ctk.CTkFrame(col, fg_color="transparent", width=width, height=1).pack()
        self.label(col, "Kontrolli i programit", size=30, strong=True, wrap=width).pack(fill="x")
        self.label(col, "Herën e parë që hapet një version i ri, programi kontrollon veten para se të fillojë. "
                        "Kjo zgjat vetëm pak sekonda.", size=15, color=GRAPHITE, wrap=width).pack(fill="x", pady=(8, 24))
        self.check_bar = ctk.CTkProgressBar(col, height=10, corner_radius=5, progress_color=INK, fg_color=RULE)
        self.check_bar.set(0)
        self.check_bar.pack(fill="x")
        self.check_count = self.label(col, "Po fillon kontrolli …", size=14, color=GRAPHITE)
        self.check_count.pack(fill="x", pady=(8, 0))
        self.check_result = self.label(col, "", size=18, strong=True, wrap=width)
        self.check_result.pack(fill="x", pady=(16, 0))
        self.check_details = ctk.CTkTextbox(col, height=150, font=self.font(13), fg_color=SHEET, text_color=TEXT,
                                            border_width=1, border_color=RULE, corner_radius=8, wrap="word")
        self.check_buttons = ctk.CTkFrame(col, fg_color="transparent")
        self.check_buttons.pack(fill="x", pady=(20, 0))

    def _start_check(self) -> None:
        self._check_queue: queue.Queue = queue.Queue()
        folder = tests_dir()

        def work():
            try:
                result = run_self_check(folder, lambda done, total: self._check_queue.put(("progress", done, total)))
            except Exception as exc:  # pytest or the tests missing from the build
                result = exc
            self._check_queue.put(("done", result))

        threading.Thread(target=work, daemon=True).start()
        self.after(60, self._poll_check)

    def _poll_check(self) -> None:
        try:
            while True:
                item = self._check_queue.get_nowait()
                if item[0] == "done":
                    self._finish_check(item[1])
                    return
                _, done, total = item
                if total:
                    self.check_bar.set(done / total)
                    self.check_count.configure(text=f"Kontrolli {done} nga {total}")
        except queue.Empty:
            pass
        self.after(60, self._poll_check)

    def _finish_check(self, result) -> None:
        if isinstance(result, CheckResult) and result.ok:
            if is_frozen():
                remember_checked_version()
            self.check_bar.set(1)
            self.check_count.configure(text=f"Kontrolli {result.total} nga {result.total}")
            self.check_result.configure(text=f"{result.total} kontrolle, të gjitha në rregull.", text_color=GREEN)
            self.button(self.check_buttons, "Vazhdo", "ink", self._leave_check, height=54, size=17,
                        width=540).pack(fill="x")
        else:
            report = self._save_check_report(result)
            if isinstance(result, CheckResult) and result.total and result.failed:
                n = len(result.failed)
                headline = (f"1 nga {result.total} kontrolle dështoi." if n == 1 else
                            f"{n} nga {result.total} kontrolle dështuan.")
                details = "\n".join(nodeid.split("::", 1)[-1] for nodeid in result.failed)
            else:
                headline = "Kontrolli nuk mund të kryhej."
                details = (f"{type(result).__name__}: {result}" if isinstance(result, Exception)
                           else result.report.strip()[-1500:])
            if report is not None:
                details += f"\n\nRaporti i plotë: {report}"
            self.check_result.configure(text=headline, text_color=RED)
            self.check_details.insert("1.0", details)
            self.check_details.configure(state="disabled")
            self.check_details.pack(fill="x", pady=(10, 0), before=self.check_buttons)
            row = self.check_buttons
            for column in range(3):
                row.grid_columnconfigure(column, weight=1, uniform="check")
            if report is not None:
                self.button(row, "Hap raportin", "plain", lambda: self._open(report), height=50, size=15).grid(
                    row=0, column=0, sticky="ew", padx=(0, 6))
            self.button(row, "Mbyll programin", "plain-red", self.destroy, height=50, size=15).grid(
                row=0, column=1, sticky="ew", padx=6)
            self.button(row, "Vazhdo gjithsesi", "ink", self._leave_check, height=50, size=15).grid(
                row=0, column=2, sticky="ew", padx=(6, 0))
        self._check_default = self._leave_check
        self.focus_input()

    @staticmethod
    def _save_check_report(result) -> Path | None:
        if isinstance(result, Exception):
            body = "".join(traceback.format_exception(type(result), result, result.__traceback__))
        else:
            body = result.report
        path = app_data_dir() / CHECK_REPORT
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{APP_NAME} {APP_VERSION}, {datetime.now():%d.%m.%Y %H:%M:%S}\n\n{body}",
                            encoding="utf-8")
            return path
        except OSError:
            return None

    def _leave_check(self) -> None:
        self._check_default = None
        self._show_screen("school")

    # ---------------------------------------------------------------- school screen
    def _build_school_screen(self) -> None:
        screen = self.school_screen = ctk.CTkFrame(self, fg_color=PAPER, corner_radius=0)
        col = ctk.CTkFrame(screen, fg_color="transparent")
        col.place(relx=0.5, rely=0.45, anchor="center")
        width = 540
        ctk.CTkFrame(col, fg_color="transparent", width=width, height=1).pack()
        self.label(col, "Cila shkollë po fotografohet?", size=30, strong=True, wrap=width).pack(fill="x")
        self.label(col, "Për shkollën krijohet një dosje te Dokumentet. Çdo klasë që përfundoni ruhet aty, "
                        "në dosjen e vet, bashkë me listën e emrave.",
                   size=15, color=GRAPHITE, wrap=width).pack(fill="x", pady=(8, 26))
        self.label(col, "Emri i shkollës", size=15, strong=True).pack(fill="x")
        self.school_entry = self.entry(col, height=56, size=20)
        self.school_entry.pack(fill="x", pady=(4, 0))
        self.school_entry.bind("<KeyRelease>", self._update_school_preview)
        self._letter_row(col, self.school_entry).pack(anchor="w", pady=(8, 0))
        self.school_path = self.label(col, "", size=13, color=GRAPHITE, wrap=width)
        self.school_path.pack(fill="x", pady=(8, 0))
        self.school_state = self.label(col, "", size=13, color=GRAPHITE, wrap=width)
        self.school_state.pack(fill="x")
        self.button(col, "Vazhdo", "ink", self.submit_school, height=54, size=17).pack(fill="x", pady=(20, 0))
        self._update_school_preview()

    def _update_school_preview(self, _event=None) -> None:
        raw = self.school_entry.get()
        folder = folder_name(raw)
        if not raw.strip():
            self.school_path.configure(text=f"Dosja do të krijohet te: {self.documents}")
            self.school_state.configure(text="Për shembull: SHFMU “Naim Frashëri”", text_color=GRAPHITE)
        elif not folder:
            self.school_path.configure(text=f"Dosja do të krijohet te: {self.documents}")
            self.school_state.configure(text="Ky emër nuk mund të përdoret si emër dosjeje.", text_color=RED)
        else:
            path = self.documents / folder
            self.school_path.configure(text=f"Dosja: {path}")
            if path.is_dir():
                self.school_state.configure(text="Kjo dosje ekziston. Puna vazhdon aty.", text_color=GREEN)
            else:
                self.school_state.configure(text="Dosja do të krijohet.", text_color=GRAPHITE)

    def submit_school(self) -> None:
        raw = self.school_entry.get()
        folder = folder_name(raw)
        if not raw.strip():
            return self._school_problem("Shkruani emrin e shkollës për të vazhduar.")
        if not folder:
            return self._school_problem("Ky emër nuk mund të përdoret si emër dosjeje.")
        path = self.documents / folder
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return self._school_problem(f"Dosja nuk u krijua: {exc.strerror or exc}")
        self.school_dir = path
        self.students = []
        self.title(f"{APP_NAME} {APP_VERSION} – {folder}")
        self._update_header()
        self._refresh_list()
        self.set_status("Shkruani emrin e nxënësit të parë.", "info")
        self._show_screen("class")
        self._offer_draft()

    def _school_problem(self, text: str) -> None:
        self.school_state.configure(text=text, text_color=RED)
        self._flash(self.school_entry, INK)
        self.school_entry.focus_set()

    # ---------------------------------------------------------------- class screen
    def _build_class_screen(self) -> None:
        screen = self.class_screen = ctk.CTkFrame(self, fg_color=PAPER, corner_radius=0)
        screen.grid_columnconfigure(0, weight=5, uniform="cols")
        screen.grid_columnconfigure(1, weight=6, uniform="cols")
        screen.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(screen, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=36, pady=(22, 14))
        self.button(head, "Përfundo shkollën", "plain", self.finish_school, height=40, size=14, width=170).pack(
            side="right", padx=(12, 0))
        self.button(head, "Hap dosjen", "plain", self.open_school_folder, height=40, size=14).pack(
            side="right", padx=(20, 0))
        self.school_title = self.label(head, "", size=24, strong=True)
        self.school_title.pack(fill="x")
        self.school_info = self.label(head, "", size=13, color=GRAPHITE)
        self.school_info.pack(fill="x")
        self.rule(screen).grid(row=1, column=0, columnspan=2, sticky="ew", padx=36)

        # left: the student being photographed
        left = ctk.CTkFrame(screen, fg_color="transparent")
        left.grid(row=2, column=0, sticky="nsew", padx=(36, 20), pady=(22, 24))
        self.label(left, "Nxënësi i radhës", size=20, strong=True).pack(fill="x")
        self.label(left, "Shkruani emrin dhe mbiemrin, pastaj shtypni Enter.", size=14,
                   color=GRAPHITE).pack(fill="x", pady=(0, 10))
        self.student_entry = self.entry(left, height=64, size=26)
        self.student_entry.pack(fill="x")
        self._letter_row(left, self.student_entry).pack(anchor="w", pady=(8, 0))
        self.button(left, "Shto nxënësin", "ink", self.add_student, height=56, size=18).pack(fill="x", pady=(12, 0))
        self.status = self.label(left, "", size=15, color=GRAPHITE, wrap=380)
        self.status.pack(fill="x", pady=(14, 0))
        left.bind("<Configure>", lambda e: self.status.configure(wraplength=max(200, int(e.width / self.scale) - 4)))
        finish = ctk.CTkFrame(left, fg_color="transparent")
        finish.pack(side="bottom", fill="x", pady=(0, 6))
        self.rule(finish).pack(fill="x", pady=(0, 14))
        self.label(finish, "Kur mbaron fotografimi i klasës:", size=14, color=GRAPHITE).pack(fill="x")
        self.button(finish, "Përfundo klasën", "green", self.finish_class, height=56, size=18).pack(
            fill="x", pady=(6, 0))

        # right: the current class, with the time each portrait was confirmed
        right = ctk.CTkFrame(screen, fg_color="transparent")
        right.grid(row=2, column=1, sticky="nsew", padx=(20, 36), pady=(22, 24))
        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(12, 0))
        self.button(actions, "Ndrysho emrin", "plain", self.edit_selected, height=40, size=14).pack(side="left")
        self.button(actions, "Fshi nga lista", "plain-red", self.delete_selected, height=40, size=14).pack(
            side="left", padx=(10, 0))
        self.label(actions, "Lista ruhet automatikisht.", size=13, color=GRAPHITE).pack(side="right")

        sheet = ctk.CTkFrame(right, fg_color=SHEET, corner_radius=10, border_width=1, border_color=RULE)
        sheet.pack(side="top", fill="both", expand=True)
        top = ctk.CTkFrame(sheet, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(14, 10))
        self.count_label = self.label(top, "", size=18, strong=True, color=INK)
        self.count_label.pack(side="right")
        self.label(top, "Klasa aktuale", size=18, strong=True).pack(side="left")
        self.rule(sheet).pack(fill="x", padx=1)
        holder = tk.Frame(sheet, bg=SHEET, bd=0, highlightthickness=0)
        holder.pack(fill="both", expand=True, padx=(8, 6), pady=(2, 10))
        s = self.scale
        self.table = ttk.Treeview(holder, columns=("nr", "name", "time"), show="headings",
                                  style="Klasa.Treeview", selectmode="browse")
        for column, text, anchor in (("nr", "Nr.", "e"), ("name", "   Emri dhe mbiemri", "w"), ("time", "Koha  ", "e")):
            self.table.heading(column, text=text, anchor=anchor)
        self.table.column("nr", width=round(54 * s), minwidth=round(40 * s), stretch=False, anchor="e")
        self.table.column("name", width=round(240 * s), minwidth=round(120 * s), stretch=True, anchor="w")
        self.table.column("time", width=round(110 * s), minwidth=round(90 * s), stretch=False, anchor="e")
        self.table.tag_configure("alt", background=ROW_ALT)
        scrollbar = ctk.CTkScrollbar(holder, command=self.table.yview, fg_color="transparent",
                                     button_color=RULE, button_hover_color=GRAPHITE)
        self.table.pack(side="left", fill="both", expand=True)

        def on_scroll(first, last):
            scrollbar.set(first, last)
            needed = float(first) > 0.0 or float(last) < 1.0
            if needed and not scrollbar.winfo_manager():
                scrollbar.pack(side="right", fill="y", before=self.table)
            elif not needed and scrollbar.winfo_manager():
                scrollbar.pack_forget()

        self.table.configure(yscrollcommand=on_scroll)
        self.empty_label = self.label(holder, "Ende nuk ka emra.\nNxënësit që shtoni shfaqen këtu, sipas radhës.",
                                      size=15, color=GRAPHITE, anchor="center", justify="center")
        self.table.bind("<Double-Button-1>", self._on_table_double_click)
        self.table.bind("<F2>", lambda e: self.edit_selected())
        self.table.bind("<Delete>", lambda e: self.delete_selected())

    def _update_header(self) -> None:
        n = count_saved_classes(self.school_dir)
        saved = ("asnjë klasë e ruajtur ende" if n == 0 else
                 "1 klasë e ruajtur" if n == 1 else f"{n} klasa të ruajtura")
        self.school_title.configure(text=self.school_dir.name)
        self.school_info.configure(text=f"{self.school_dir}   ({saved})")

    def _refresh_list(self, select: int | None = None) -> None:
        table = self.table
        table.delete(*table.get_children())
        today = date.today()
        shown_times = []
        for i, student in enumerate(self.students):
            shown = list_time(student.taken, today)
            shown_times.append(shown)
            table.insert("", "end", iid=str(i), values=(f"{i + 1}.", f"   {student.name}", f"{shown}  "),
                         tags=("alt",) if i % 2 else ())
        # a time from another day also shows its date, so the column grows to fit it
        widest = max([self.list_font.measure(f"{t}  ") for t in shown_times] + [0])
        table.column("time", width=max(round(110 * self.scale), widest + round(14 * self.scale)))
        if select is not None and 0 <= select < len(self.students):
            table.selection_set(str(select))
            table.focus(str(select))
            table.see(str(select))
        elif self.students:
            table.see(str(len(self.students) - 1))
        self.count_label.configure(text=f"{len(self.students)} nxënës")
        if self.students:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.45, anchor="center")

    def _selected(self) -> int | None:
        selection = self.table.selection()
        return int(selection[0]) if selection else None

    def _on_table_double_click(self, event):
        if self.table.identify_region(event.x, event.y) == "cell":
            self.edit_selected()
            return "break"
        return None

    # ---------------------------------------------------------------- actions
    def add_student(self) -> None:
        if self.modal is not None or self.school_dir is None:
            return
        name = clean_name(self.student_entry.get())
        if not name:
            self.student_entry.delete(0, "end")
            self.set_status("Shkruani emrin e nxënësit para se ta shtoni.", "warn")
            self._flash(self.student_entry, INK)
            self.student_entry.focus_set()
            return
        number = len(self.students) + 1
        modal = Modal(self, "A u bë fotografia?", default="yes", cancel="no",
                      buttons=[("no", "Jo ende (Esc)", "plain"), ("yes", "Po, u bë (Enter)", "green")])
        modal.add_badge(self.school_dir.name, name, f"Nr. {number} në listën e klasës")
        twin = next((i for i, s in enumerate(self.students) if same_name(s.name) == same_name(name)), None)
        if twin is not None:
            modal.add_text(f"Ky emër është tashmë në listë (nr. {twin + 1}). Nëse është nxënës tjetër "
                           "me të njëjtin emër, vazhdoni.", color=AMBER, size=14, pady=(14, 0))
        modal.add_text("Nëse portreti është bërë, emri shtohet në listë dhe kalohet te nxënësi tjetër.",
                       pady=(16, 0))
        if self.ask(modal) != "yes":
            return
        taken = datetime.now().replace(microsecond=0)
        self.students.append(Student(name, taken))
        self._refresh_list()
        self.student_entry.delete(0, "end")
        self._changed(f"U shtua në orën {taken:%H:%M:%S}: {name} (nr. {len(self.students)}).")

    def edit_selected(self) -> None:
        if self.modal is not None:
            return
        i = self._selected()
        if i is None:
            self.set_status("Zgjidhni një emër në listë, pastaj provoni përsëri.", "warn")
            return
        old = self.students[i]
        modal = Modal(self, "Ndrysho emrin", default="save", cancel="cancel",
                      buttons=[("cancel", "Anulo", "plain"), ("save", "Ruaj emrin", "ink")])
        modal.add_text(f"Nr. {i + 1} në listë{self._taken_phrase(old.taken)}.")
        field = self.entry(modal.body, height=54, size=22)
        field.pack(fill="x", pady=(12, 0))
        field.insert(0, old.name)
        field.select_range(0, "end")
        field.icursor("end")
        modal.watch(field)
        self._letter_row(modal.body, field).pack(anchor="w", pady=(8, 0))
        chosen = {}

        def validate(_key):
            chosen["name"] = clean_name(field.get())
            return None if chosen["name"] else "Emri nuk mund të jetë bosh."

        modal.validate, modal.focus_widget = validate, field
        if self.ask(modal) != "save" or chosen["name"] == old.name:
            return
        self.students[i] = Student(chosen["name"], old.taken)  # the photo time stays the same
        self._refresh_list(select=i)
        self._changed(f"Emri u ndryshua në {chosen['name']} (ishte {old.name}).")

    @staticmethod
    def _taken_phrase(taken: datetime | None) -> str:
        if taken is None:
            return ""
        if taken.date() == date.today():
            return f", fotografuar në orën {taken:%H:%M:%S}"
        return f", fotografuar më {taken:%d.%m.%Y} në orën {taken:%H:%M:%S}"

    def delete_selected(self) -> None:
        if self.modal is not None:
            return
        i = self._selected()
        if i is None:
            self.set_status("Zgjidhni një emër në listë, pastaj provoni përsëri.", "warn")
            return
        modal = Modal(self, "Të fshihet nga lista?", default="delete", cancel="cancel",
                      buttons=[("cancel", "Anulo", "plain"), ("delete", "Fshi", "red")])
        modal.add_text(self.students[i].name, color=TEXT, size=22, strong=True, pady=(14, 0))
        modal.add_text(f"Nr. {i + 1} në listë{self._taken_phrase(self.students[i].taken)}.", pady=(2, 0))
        if self.ask(modal) != "delete":
            return
        removed = self.students.pop(i)
        self._refresh_list(select=min(i, len(self.students) - 1) if self.students else None)
        self._changed(f"U fshi nga lista: {removed.name}.", "info")

    def finish_class(self) -> None:
        if self.modal is not None or self.school_dir is None:
            return
        if not self.students:
            modal = Modal(self, "Lista është bosh", default="ok", cancel="ok",
                          buttons=[("ok", "Në rregull", "ink")])
            modal.add_text("Shtoni të paktën një nxënës para se ta përfundoni klasën.")
            self.ask(modal)
            return

        modal = Modal(self, "Përfundo klasën", default="save", cancel="cancel",
                      buttons=[("cancel", "Anulo", "plain"), ("save", "Ruaj klasën", "green")])
        modal.add_text(f"Lista ka {len(self.students)} nxënës. Emrat ruhen në një skedar .txt si listë me numra, "
                       "bashkë me datën dhe orën e fotografimit.")
        self.label(modal.body, "Emri i klasës", size=15, strong=True).pack(fill="x", pady=(18, 4))
        field = self.entry(modal.body, height=52, size=20)
        field.pack(fill="x")
        preview = self.label(modal.body, "", size=13, color=GRAPHITE, wrap=modal.width)
        preview.pack(fill="x", pady=(6, 0))
        self.label(modal.body, "Renditja e emrave", size=15, strong=True).pack(fill="x", pady=(16, 4))
        order = tk.StringVar(master=self, value=self.sort_choice)
        for value, caption in (("alpha", "Sipas alfabetit shqip (A, B, C, Ç, D, Dh, E, Ë …)"),
                               ("entry", "Sipas radhës së fotografimit")):
            ctk.CTkRadioButton(modal.body, text=caption, variable=order, value=value, font=self.font(15),
                               text_color=TEXT, fg_color=INK, hover_color=INK_HOVER,
                               border_color=GRAPHITE).pack(anchor="w", pady=5)

        def update_preview():
            raw = field.get()
            folder = folder_name(raw)
            if not raw.strip():
                preview.configure(text="Shembull: X-1, X-2, XI-3", text_color=GRAPHITE)
            elif not folder:
                preview.configure(text="Ky emër nuk mund të përdoret si emër dosjeje.", text_color=RED)
            else:
                existing = count_names_in(self.school_dir / folder / f"{folder}.txt")
                if existing:
                    preview.configure(text=f"Kjo klasë ekziston dhe ka {count_names(existing)}. "
                                           "Do të pyeteni çfarë të bëni me to.", text_color=AMBER)
                else:
                    preview.configure(text=f"Ruhet te: {self.school_dir / folder / (folder + '.txt')}",
                                      text_color=GRAPHITE)

        modal.watch(field, update_preview)
        update_preview()
        chosen = {}

        def validate(_key):
            raw = field.get()
            if not raw.strip():
                return "Shkruani emrin e klasës, p.sh. X-1."
            chosen["folder"] = folder_name(raw)
            if not chosen["folder"]:
                return "Ky emër nuk mund të përdoret si emër dosjeje."
            chosen["alphabetical"] = order.get() == "alpha"
            return None

        modal.validate, modal.focus_widget = validate, field
        if self.ask(modal) != "save":
            return
        folder, alphabetical = chosen["folder"], chosen["alphabetical"]
        self.sort_choice = "alpha" if alphabetical else "entry"

        merge = False
        existing = count_names_in(self.school_dir / folder / f"{folder}.txt")
        if existing:
            modal = Modal(self, f"Klasa {folder} ka tashmë një listë", default="merge", cancel="cancel",
                          width=580, buttons=[("cancel", "Anulo", "plain"),
                                              ("replace", "Zëvendëso listën", "red"),
                                              ("merge", "Shtoji te lista", "green")])
            modal.add_text(f"Skedari {folder}.txt ka {count_names(existing)}. Çfarë të bëhet me emrat e rinj?")
            modal.add_text("Shtoji te lista: emrat e rinj u shtohen atyre që janë aty, pa përsëritje.",
                           color=TEXT, pady=(14, 0))
            modal.add_text("Zëvendëso listën: lista e vjetër fshihet dhe mbetet vetëm lista e re.",
                           color=TEXT, pady=(6, 0))
            choice = self.ask(modal)
            if choice not in ("merge", "replace"):
                return
            merge = choice == "merge"

        new_count = len(self.students)
        try:
            path, final, skipped = save_class(self.school_dir, folder, self.students, alphabetical, merge)
        except OSError as exc:
            modal = Modal(self, "Lista nuk u ruajt", default="ok", cancel="ok",
                          buttons=[("ok", "Në rregull", "ink")])
            if isinstance(exc, PermissionError):
                modal.add_text(f"Skedari {folder}.txt është i hapur ose i bllokuar nga një program tjetër "
                               "(p.sh. Excel). Mbylleni atë dhe provoni përsëri.")
            else:
                modal.add_text(f"Gabimi: {exc.strerror or exc}")
            modal.add_text("Emrat mbeten në listë, asgjë nuk humbet.", color=TEXT)
            self.ask(modal)
            return

        self.students = []
        self._refresh_list()
        self._update_header()
        self._changed(f"Klasa {folder} u ruajt me {len(final)} nxënës.")

        how = "sipas alfabetit shqip" if alphabetical else "sipas radhës së fotografimit"
        modal = Modal(self, "Klasa u ruajt", default="next", cancel="next",
                      buttons=[("open", "Hap dosjen", "plain"), ("next", "Vazhdo me klasën tjetër", "ink")])
        modal.add_text(folder, color=INK, size=28, strong=True, pady=(12, 0))
        if merge:
            added = new_count - len(skipped)
            news = ("Nuk u shtua asnjë emër i ri." if added == 0 else
                    "U shtua 1 emër i ri." if added == 1 else f"U shtuan {added} emra të rinj.")
            modal.add_text(f"{news} Lista tani ka {len(final)} nxënës, renditur {how}.", color=TEXT)
        else:
            modal.add_text(f"{len(final)} nxënës, renditur {how}.", color=TEXT)
        modal.add_text(str(path), size=13, pady=(4, 0))
        if len(skipped) == 1:
            modal.add_text(f"Emri {skipped[0].name} ishte tashmë në listë dhe nuk u shtua përsëri.",
                           color=AMBER, size=14, pady=(12, 0))
        elif skipped:
            modal.add_text(f"Këta {len(skipped)} emra ishin tashmë në listë dhe nuk u shtuan përsëri: "
                           f"{', '.join(s.name for s in skipped)}.", color=AMBER, size=14, pady=(12, 0))

        def open_class_folder():
            try:
                open_folder(path.parent)
            except Exception as exc:
                modal.show_error(f"Dosja nuk u hap: {exc}")

        modal.actions["open"] = open_class_folder  # the dialog stays open until "Vazhdo me klasën tjetër"
        self.ask(modal)

    def finish_school(self) -> None:
        """Close this school and go back to the start screen for the next one."""
        if self.modal is not None or self.school_dir is None:
            return
        classes, total = school_summary(self.school_dir)
        unsaved = len(self.students)
        modal = Modal(self, "Të përfundohet shkolla?", default="cancel" if unsaved else "finish", cancel="cancel",
                      buttons=[("cancel", "Anulo", "plain"), ("finish", "Përfundo shkollën", "ink")])
        modal.add_text(self.school_dir.name, color=INK, size=22, strong=True, pady=(12, 0))
        if classes == 0:
            summary = "Në këtë shkollë nuk është ruajtur ende asnjë klasë."
        elif classes == 1:
            summary = f"Në këtë shkollë është ruajtur 1 klasë me {total} nxënës."
        else:
            summary = f"Në këtë shkollë janë ruajtur {classes} klasa me {total} nxënës gjithsej."
        modal.add_text(summary, color=TEXT)
        if unsaved and self._save_draft():
            modal.add_text(f"Klasa aktuale ka {unsaved} nxënës dhe ende nuk është ruajtur si klasë. Lista ruhet "
                           "automatikisht dhe do t'ju ofrohet sërish kur ta hapni këtë shkollë.",
                           color=AMBER, size=14, pady=(12, 0))
        elif unsaved:
            modal.add_text(f"Kujdes: lista aktuale ({unsaved} nxënës) nuk mund të ruhej automatikisht. "
                           "Nëse e përfundoni shkollën tani, këta emra humbasin.", color=RED, size=14, pady=(12, 0))
        modal.add_text("Pastaj kthehemi te fillimi, për shkollën tjetër.", pady=(12, 0))
        if self.ask(modal) != "finish":
            return
        finished = self.school_dir.name
        self.school_dir = None
        self.students = []
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.school_entry.delete(0, "end")
        self._update_school_preview()
        self.school_state.configure(text=f"Shkolla {finished} u përfundua. Shkruani emrin e shkollës tjetër.",
                                    text_color=GREEN)
        self._show_screen("school")

    def open_school_folder(self) -> None:
        if self.school_dir is not None:
            self._open(self.school_dir)

    def _open(self, path: Path) -> None:
        try:
            open_folder(path)
        except Exception as exc:
            self.set_status(f"Dosja nuk u hap: {exc}", "error")

    # ---------------------------------------------------------------- ë and ç
    def _type_into(self, field: ctk.CTkEntry, letter: str) -> None:
        self._insert_letter(field._entry, letter)

    def _type_letter(self, letter: str) -> str:
        """Alt+E / Alt+C: type ë / ç into the field that has the cursor."""
        if self.screen == "check":
            return "break"
        widget = self.focus_get()
        if isinstance(widget, tk.Entry):
            target = widget
        elif self.modal is None:
            target = (self.student_entry if self.screen == "class" else self.school_entry)._entry
        else:
            return "break"
        self._insert_letter(target, letter)
        return "break"

    @staticmethod
    def _insert_letter(target: tk.Entry, letter: str) -> None:
        target.focus_set()
        if target.selection_present():
            target.delete("sel.first", "sel.last")
        target.insert("insert", letter)
        target.event_generate("<KeyRelease>")  # refresh previews that follow the typing

    # ---------------------------------------------------------------- autosave of the current class
    def _draft_path(self) -> Path:
        return self.school_dir / DRAFT_FILE

    def _save_draft(self) -> bool:
        try:
            if self.students:
                write_lines(self._draft_path(), numbered_lines(self.students))
            elif self._draft_path().exists():
                self._draft_path().unlink()
            self.draft_ok = True
        except OSError:
            self.draft_ok = False
        return self.draft_ok

    def _changed(self, message: str, kind: str = "ok") -> None:
        if not self._save_draft():
            message += "  Kujdes: kopja automatike e listës nuk u ruajt."
            kind = "warn"
        self.set_status(message, kind)

    def _offer_draft(self) -> None:
        try:
            students = read_students(self._draft_path()) if self._draft_path().is_file() else []
        except OSError:
            students = []
        if not students:
            return
        sample = ", ".join(s.name for s in students[:3]) + (" …" if len(students) > 3 else "")
        modal = Modal(self, "Listë e papërfunduar", default="restore", cancel="new",
                      buttons=[("new", "Fillo listë të re", "plain"), ("restore", "Vazhdo listën", "ink")])
        modal.add_text(f"Herën e kaluar mbeti një klasë e paruajtur me {len(students)} nxënës:")
        modal.add_text(sample, color=TEXT, pady=(6, 0))
        modal.add_text("Dëshironi ta vazhdoni?", pady=(12, 0))
        if self.ask(modal) == "restore":
            self.students = students
            self._refresh_list()
            self.set_status(f"Lista u rikthye: {len(students)} nxënës.", "ok")

    # ---------------------------------------------------------------- keyboard, focus, status
    def ask(self, modal: Modal) -> str:
        result = modal.run()
        self.focus_input()
        return result

    def focus_input(self) -> None:
        if self.modal is None:
            if self.screen == "check":
                self.check_screen.focus_set()
            else:
                (self.student_entry if self.screen == "class" else self.school_entry).focus_set()

    def _show_screen(self, name: str) -> None:
        self.screen = name
        screens = {"check": self.check_screen, "school": self.school_screen, "class": self.class_screen}
        for frame in screens.values():
            frame.pack_forget()
        screens[name].pack(fill="both", expand=True)
        self.focus_input()

    def _on_enter(self, event) -> str:
        if self.modal is not None:
            self.modal.press_default()
        elif self.screen == "check":
            if self._check_default is not None:
                self._check_default()
        elif self.screen == "school":
            self.submit_school()
        elif event.widget is self.table:
            self.edit_selected()
        else:
            self.add_student()
        return "break"

    def _on_escape(self, _event) -> str:
        if self.modal is not None:
            self.modal.press_cancel()
        elif self.screen == "class":
            self.student_entry.delete(0, "end")
            self.student_entry.focus_set()
        return "break"

    def _on_key(self, event):
        """Typing while the list or a button has the focus still goes into the name field."""
        if self.modal is not None or self.screen != "class" or isinstance(event.widget, tk.Entry):
            return None
        if len(event.char) == 1 and event.char.isprintable():
            self.student_entry.focus_set()
            self.student_entry.insert("end", event.char)
            return "break"
        return None

    def set_status(self, text: str, kind: str = "info") -> None:
        self.status.configure(text=text, text_color=STATUS_COLORS[kind])

    def _flash(self, entry: ctk.CTkEntry, normal: str) -> None:
        entry.configure(border_color=RED)
        self.after(700, lambda: entry.winfo_exists() and entry.configure(border_color=normal))

    # ---------------------------------------------------------------- closing and errors
    def on_close(self) -> None:
        if self.modal is not None:
            self.modal.press_cancel()
            return
        if self.students:
            modal = Modal(self, "Të mbyllet programi?", default="stay", cancel="stay",
                          buttons=[("stay", "Mbetu", "ink"), ("close", "Mbyll programin", "plain")])
            if self._save_draft():
                modal.add_text(f"Klasa aktuale ka {len(self.students)} nxënës dhe ende nuk është ruajtur si klasë. "
                               "Lista ruhet automatikisht dhe do t'ju ofrohet sërish kur ta hapni këtë shkollë.")
            else:
                modal.add_text(f"Kujdes: lista aktuale ({len(self.students)} nxënës) nuk mund të ruhej "
                               "automatikisht. Nëse e mbyllni programin tani, këta emra humbasin.", color=RED)
            if self.ask(modal) != "close":
                return
        self.destroy()

    def report_callback_exception(self, exc, value, tb) -> None:
        details = "".join(traceback.format_exception(exc, value, tb))
        if sys.stderr:
            print(details, file=sys.stderr)
        messagebox.showerror(APP_NAME, "Ndodhi një gabim i papritur. Lista e klasës aktuale ruhet automatikisht."
                                       "\n\n" + details[-1500:], parent=self)


def main() -> None:
    try:
        app = App(force_check="--kontrollo" in sys.argv[1:])
    except Exception:
        details = traceback.format_exc()
        if sys.stderr:
            print(details, file=sys.stderr)
        with contextlib.suppress(Exception):
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(APP_NAME, "Programi nuk mund të hapej.\n\n" + details[-1500:], parent=root)
            root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
