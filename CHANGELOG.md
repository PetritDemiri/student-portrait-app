# Changelog

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
