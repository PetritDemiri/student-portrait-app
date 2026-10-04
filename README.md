# Foto Nxënësit

A small Windows app for school badge photo sessions. Type each student's name, confirm that the portrait was taken, and when the class is done you get a numbered class list with the date and time of every photo, sorted by the Albanian alphabet if you want.

The interface is in Albanian. Student names never leave your computer.

**[Download the latest version](../../releases/latest)**: a single `FotoNxenesit.exe`, nothing to install.

## How it works

1. **School.** Type the school's name. A folder with that name is created in your Documents folder, or reused if it already exists.
2. **Students.** Type a student's full name and press Enter. A badge preview asks whether the photo was taken: Enter adds the name to the class list with the time, Esc keeps it in the field for later.
3. **Finish the class.** Click *Përfundo klasën*, type the class name (X-1, X-2 …) and choose the order: Albanian alphabet or photographing order. The list is saved, and cleared for the next class.
4. **Finish the school.** *Përfundo shkollën* shows how many classes and students were saved, then goes back to the start for the next school.

```
Documents\
└── SHFMU “Naim Frashëri”\
    ├── X-1\
    │   └── X-1.txt
    └── X-2\
        └── X-2.txt
```

Each class file is a numbered list with the date and time each portrait was confirmed, ending with the class total:

```
1. Arta Krasniqi – 01.10.2026 09:42:17
2. Besnik Gashi – 01.10.2026 09:43:05
3. Çlirim Hoxha – 01.10.2026 09:44:51

Gjithsej: 3 nxënës në klasën X-1
```

The files are UTF-8 with Windows line endings, so ë and ç show correctly in Notepad, Word and Excel. If OneDrive manages your Documents folder, the school folder is created there. The times come from the computer's clock: to match names to photos by time, set the camera's clock to the same time.

## Albanian alphabetical order

`A B C Ç D Dh E Ë F G Gj H I J K L Ll M N Nj O P Q R Rr S Sh T Th U V X Xh Y Z Zh`

Digraphs count as single letters, so *Syla* comes before *Shala* and *Tushi* before *Thaçi*. Names are compared word by word, in the order they were typed: to sort by surname, type the surname first. Letters from other languages sit next to the closest Albanian letter (*Čolić* after the C names, *W* between V and X).

## Keyboard

| Key | What it does |
| --- | --- |
| Enter | Add the student, or confirm the photo |
| Esc | "Not yet" in the photo dialog, or clear the name field |
| Alt+E / Alt+C | Type ë / ç (the ë and ç buttons under the name field do the same) |
| Double-click or F2 | Edit the selected name |
| Delete | Remove the selected name |

## Safety nets

- The class in progress is saved after every change (`_klasa e papërfunduar.txt` in the school folder) and offered back the next time that school is opened, so a crash or an accidental close loses nothing.
- A name that's already on the list shows a warning. It can still be added, since two students can share a name.
- Saving a class that already has a list asks whether to add the new names to it (repeats are skipped) or replace it. Lists saved by version 1.0.0 are read too; their names simply have no time.
- Characters Windows doesn't allow in folder names are converted: `"` becomes “ ”, and `/` `\` `:` become `-`, so *X/1* is saved as *X-1*.

The `.exe` isn't code-signed, so the first launch may show "Windows protected your PC". Click **More info**, then **Run anyway**.

## Building it yourself

You need Windows and Python 3.10 or newer with Tcl/Tk, which the python.org installer includes by default. Double-click `build.bat`, or run:

```
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --onefile --windowed --name FotoNxenesit --collect-data customtkinter foto_nxenesit.py
```

The program ends up in `dist\FotoNxenesit.exe`. To run it from source instead: `py foto_nxenesit.py`.

Tests for the sorting and the class files: install pytest once with `py -m pip install -r requirements-dev.txt`, then type `pytest` in the project folder.

GitHub Actions runs the tests and builds the `.exe` on every push to `main`. Pushing a tag that starts with `v` (for example `v1.0.0`) also publishes the `.exe` as a release.

Two settings sit at the top of `foto_nxenesit.py`: `AUTO_CAPITALIZE` turns "arta krasniqi" into "Arta Krasniqi", and `TXT_ENCODING` can be changed to `"utf-8"` if another program shows `ï»¿` before the first name.

## Shkurt në shqip

**Foto Nxënësit** është një program i vogël për Windows që ndihmon gjatë fotografimit të nxënësve për kartelat e shkollës.

1. Shkarkoni `FotoNxenesit.exe` nga [versioni i fundit](../../releases/latest) dhe hapeni. Nuk ka nevojë për instalim.
2. Shkruani emrin e shkollës. Te Dokumentet krijohet një dosje me këtë emër.
3. Për çdo nxënës shkruani emrin dhe mbiemrin, shtypni Enter dhe, pasi të bëhet fotografia, shtypni Enter përsëri. Programi shënon datën dhe orën e fotografisë.
4. Kur mbaron klasa, shtypni **Përfundo klasën**, shkruani emrin e klasës (p.sh. X-1) dhe zgjidhni renditjen: sipas alfabetit shqip ose sipas radhës së fotografimit. Lista ruhet te `Dokumentet\<shkolla>\<klasa>\<klasa>.txt` me numra, me datën dhe orën e çdo fotografie dhe me numrin e nxënësve në fund.
5. Kur mbaron shkolla, shtypni **Përfundo shkollën** për të kaluar te shkolla tjetër.

Nëse tastiera nuk ka ë dhe ç, përdorni butonat nën fushën e emrit ose Alt+E dhe Alt+C.

Lista ruhet automatikisht gjatë punës, kështu që emrat nuk humbin nëse programi mbyllet papritur. Emrat e nxënësve mbeten vetëm në kompjuterin tuaj.

Herën e parë Windows mund të shfaqë paralajmërimin “Windows protected your PC”: zgjidhni **More info** dhe pastaj **Run anyway**.

## License

MIT, see [LICENSE](LICENSE).
