# Changelog

## 1.4.1 – 2026-10-06

### Changed
- `kontrolli.txt` records the whole result of the self-check instead of only the version: the date, the version, the result, how many checks there were and how many passed, failed or were skipped, how long it took, and the system it ran on. A failed check is written down too, with the names of the failed checks, and the check runs again on the next start.
- The check is skipped only when the record shows that this version passed with no failures.

## 1.4.0 – 2026-10-06

### Added
- *Klasat e ruajtura*, on the start screen and during a session, to read and correct the class lists that are already saved. From the start screen it lists every school with saved classes; during a session it opens that school's classes, and *Kthehu* returns to the class being photographed.
- In a saved list: add a name (without a photo time), rename, delete, sort by the Albanian alphabet, and move a student to another class, existing or new. Nothing is written until *Ruaj ndryshimet* (or Ctrl+S), and leaving with unsaved changes asks first.
- *Hap në Notepad* opens the list as it is; when it is saved there, the program reads it again. If the list also has unsaved changes in the program, saving asks which one to keep.
- *Kthe versionin e mëparshëm*: before the program changes a saved list, it keeps the version before it in `Documents\FotoNxenesit\kopje`, and one click brings it back.

### Changed
- Adding to or replacing a class list when a class is finished also keeps the old list as that copy.
- The second line of a screen's header wraps instead of being cut off.

## 1.3.2 – 2026-10-04

### Changed
- In the "Klasa u ruajt" dialog, "Hap dosjen" opens the class folder and leaves the dialog open; only "Vazhdo me klasën tjetër" (or Enter) closes it.

## 1.3.1 – 2026-10-04

### Changed
- The self-check keeps its two small files (`kontrolli.txt` and, after a failed check, `kontrolli-raporti.txt`) in `Documents\FotoNxenesit` instead of the hidden `%LOCALAPPDATA%\FotoNxenesit`.

## 1.3.0 – 2026-10-04

### Added
- The first time each new version starts, the program runs its tests in a window before opening, with a progress bar and the result. If a check fails, it names it, saves a report, and lets you continue or close.
- `--kontrollo` shows the same check when running from source.

### Changed
- pytest is now part of `requirements.txt` (it is packed into the `.exe`), so `requirements-dev.txt` is gone.

## 1.2.0 – 2026-10-04

### Changed
- The finish-class dialog shows the full path where the class file will be saved, not just the part from the school folder on.

## 1.1.0 – 2026-10-01

### Added
- The date and time of each portrait is recorded when it is confirmed, shown in the app and written to the class file.
- Class files are numbered lists, in both orders, and end with the class total, for example `Gjithsej: 24 nxënës në klasën X-1`.
- *Përfundo shkollën* button: shows how many classes and students were saved for the school, then returns to the start screen for the next school.
- ë and ç buttons under the name fields, and the Alt+E / Alt+C shortcuts, for keyboards without those letters.

### Changed
- The current class is shown as a table with number, name and time.
- Editing a name or restoring an unfinished list keeps the photo times.
- Adding names to a class list saved by 1.0.0 keeps its names; they have no time.

## 1.0.0 – 2026-10-01

First release.
- A folder per school in Documents, and a text file per class.
- Badge-style confirmation for every portrait before the name is added.
- Albanian alphabetical order, with digraphs counted as single letters.
- Autosave of the class in progress, duplicate warning, and merge or replace for classes that already have a list.
- Single-file Windows build with PyInstaller, and releases built by GitHub Actions.
