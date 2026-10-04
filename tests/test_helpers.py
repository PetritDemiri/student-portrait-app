"""Tests for the parts of foto_nxenesit that don't need a window.

Run from the project folder:  pytest
"""
import random
from datetime import date, datetime

import pytest

import foto_nxenesit as app


def assert_order(names):
    """The names must come out in exactly this order, whatever order they go in."""
    names = list(names)
    for seed in range(5):
        shuffled = names[:]
        random.Random(seed).shuffle(shuffled)
        assert app.sort_albanian(shuffled) == names


def order_id(names):
    return " < ".join(names)


# ------------------------------------------------------------------ Albanian alphabetical order
@pytest.mark.parametrize("names", [
    ("Syla", "Shala"), ("Tushi", "Thaçi"), ("Lushaku", "Llapashtica"), ("Zymberi", "Zhuri"),
    ("Nora", "Nuhiu", "Njomza"), ("Rama", "Rugova", "Rrahmani"), ("Dushi", "Dhurata"),
    ("Xoxa", "Xhaka"), ("Gashi", "Gzimi", "Gjergji"),
], ids=order_id)
def test_digraphs_are_single_letters(names):
    assert_order(names)


@pytest.mark.parametrize("names", [
    ("Kaçaku", "Kadriu"), ("Hasani", "Hasi", "Hashani"), ("Mazreku", "Mehmeti", "Mëhmeti"),
    ("Morina", "Mulaku", "Mulliqi"), ("Bekteshi", "Beqiri", "Berisha"),
    ("Erza", "Ëndrit", "Fatmir"), ("Cufaj", "Çlirim", "Dardan"),
], ids=order_id)
def test_letters_inside_words(names):
    assert_order(names)


@pytest.mark.parametrize("names", [
    ("Ana Zeka", "Anabela Berisha"), ("Arta", "Arta Krasniqi", "Arta Mustafa"),
    ("Ana Berisha", "Ana Gashi", "Ana-Maria Gashi"),
], ids=order_id)
def test_word_by_word(names):
    assert_order(names)


@pytest.mark.parametrize("names", [
    ("Cufaj", "Čolić", "Çlirim"), ("Valon", "William", "Xeni"), ("Syzana", "Šehu", "Shqipe"),
    ("Zana", "Žarko", "Zhaneta"),
], ids=order_id)
def test_letters_from_other_languages(names):
    assert_order(names)


def test_whole_alphabet():
    assert_order([
        "Agon", "Arta", "Besnik", "Blerina", "Çlirim", "Dardan", "Donika", "Dhurata", "Elira", "Ëndrit",
        "Fjolla", "Gentrit", "Gresa", "Gjergj", "Hana", "Ilir", "Jeton", "Kaltrina", "Liridon", "Lluka",
        "Mimoza", "Nora", "Njomza", "Orges", "Petrit", "Qendresa", "Rina", "Rrezon", "Sara", "Syzana",
        "Shqipe", "Teuta", "Thëllëza", "Uran", "Valon", "Xeni", "Xhemile", "Yll", "Zana", "Zhaneta"])


def test_upper_and_lower_case_sort_the_same():
    assert app.sort_albanian(["DHURATA", "Dea", "dardan"]) == ["dardan", "Dea", "DHURATA"]


def test_decomposed_letters():
    decomposed = "E\u0308ndrit"  # E followed by a combining diaeresis
    assert app.sort_albanian([decomposed, "Fisnik", "Erza"]) == ["Erza", decomposed, "Fisnik"]


# ------------------------------------------------------------------ names and folder names
@pytest.mark.parametrize("raw, expected", [
    ("  arta   krasniqi ", "Arta Krasniqi"), ("ARTA KRASNIQI", "ARTA KRASNIQI"),
    ("ëndrit berisha", "Ëndrit Berisha"), ("arta-maria gashi", "Arta-Maria Gashi"),
    ("çlirim hoxha", "Çlirim Hoxha"), ("dhurata", "Dhurata"), ("   ", ""), ("E\u0308ndrit", "Ëndrit"),
])
def test_clean_name(raw, expected):
    assert app.clean_name(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ('SHFMU "Naim Frashëri"', "SHFMU “Naim Frashëri”"), ("X/1", "X-1"), ("XII\\3", "XII-3"), ("X-1", "X-1"),
    ("  X  -  1 ", "X - 1"), ("Shkolla.", "Shkolla"), ("a<b>c|d?e*", "abcde"), ("CON", "_CON"),
    ("nul.txt", "_nul.txt"), ("...", ""), ("", ""),
])
def test_folder_name(raw, expected):
    assert app.folder_name(raw) == expected


# ------------------------------------------------------------------ class files
T1 = datetime(2026, 10, 1, 9, 40, 2)
T2 = datetime(2026, 10, 1, 9, 42, 17)
T3 = datetime(2026, 10, 1, 9, 44, 51)


@pytest.fixture
def school(tmp_path):
    folder = tmp_path / "Shkolla"
    folder.mkdir()
    return folder


def save(school, students, alphabetical=True, merge=False, folder="X-1"):
    return app.save_class(school, folder, students, alphabetical=alphabetical, merge=merge)


def test_alphabetical_file_is_numbered_with_times_and_total(school):
    path, _, _ = save(school, [app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2),
                               app.Student("Çlirim Berisha", T3)])
    assert path.relative_to(school).parts == ("X-1", "X-1.txt")
    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM"
    assert data[3:].decode("utf-8") == ("1. Arta Gashi – 01.10.2026 09:42:17\r\n"
                                        "2. Çlirim Berisha – 01.10.2026 09:44:51\r\n"
                                        "3. Zana Hoxha – 01.10.2026 09:40:02\r\n"
                                        "\r\n"
                                        "Gjithsej: 3 nxënës në klasën X-1")
    assert [p.name for p in path.parent.iterdir()] == ["X-1.txt"], "no temporary files left"


def test_photographing_order_is_numbered_too(school):
    path, _, _ = save(school, [app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2)], alphabetical=False)
    lines = app.read_text(path).splitlines()
    assert lines[:2] == ["1. Zana Hoxha – 01.10.2026 09:40:02", "2. Arta Gashi – 01.10.2026 09:42:17"]
    assert lines[-1] == "Gjithsej: 2 nxënës në klasën X-1"


def test_file_reads_back_the_same_students(school):
    students = [app.Student("Arta Gashi", T2), app.Student("Ana - Maria Krasniqi", T3), app.Student("Besa", None)]
    path, final, _ = save(school, students, alphabetical=False)
    assert app.read_students(path) == final


def test_merge_skips_names_already_in_the_file_and_recounts(school):
    save(school, [app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2)])
    path, final, skipped = save(school, [app.Student("arta gashi", T3), app.Student("Besa Krasniqi", T3)], merge=True)
    assert [s.name for s in final] == ["Arta Gashi", "Besa Krasniqi", "Zana Hoxha"]
    assert final[0].taken == T2, "the time already in the file is kept"
    assert [s.name for s in skipped] == ["arta gashi"]
    assert app.read_text(path).splitlines()[-1] == "Gjithsej: 3 nxënës në klasën X-1"


def test_merge_with_a_list_saved_by_version_1_0_0(school):
    folder = school / "X-1"
    folder.mkdir()
    (folder / "X-1.txt").write_bytes("\ufeffZana Hoxha\r\nArta Gashi".encode("utf-8"))
    path, final, _ = save(school, [app.Student("Yll Morina", T3)], alphabetical=False, merge=True)
    assert final == [app.Student("Zana Hoxha"), app.Student("Arta Gashi"), app.Student("Yll Morina", T3)]
    assert app.read_text(path).splitlines()[:3] == ["1. Zana Hoxha", "2. Arta Gashi",
                                                    "3. Yll Morina – 01.10.2026 09:44:51"]


def test_replace(school):
    save(school, [app.Student("Zana Hoxha", T1)])
    path, _, _ = save(school, [app.Student("Dea Rama", T2)])
    assert app.read_students(path) == [app.Student("Dea Rama", T2)]


def test_parsing_ignores_numbers_and_total_but_keeps_names_with_dashes():
    text = ("1. Ana - Maria Gashi – 01.10.2026 09:42:17\n"
            "2) Besa Krasniqi - 30.09.2026 14:05\n"
            "Dea Rama\n\n"
            "Gjithsej: 3 nxënës në klasën X-1\n")
    assert app.parse_students(text) == [app.Student("Ana - Maria Gashi", T2),
                                        app.Student("Besa Krasniqi", datetime(2026, 9, 30, 14, 5)),
                                        app.Student("Dea Rama")]


def test_reads_lists_saved_in_the_old_windows_encoding(school):
    old = school / "old.txt"
    old.write_bytes("Ëndrit Çela\r\nArta\r\n\r\n".encode("cp1250"))
    assert [s.name for s in app.read_students(old)] == ["Ëndrit Çela", "Arta"]


def test_school_summary(school):
    save(school, [app.Student("Arta", T1), app.Student("Besa", T2)], folder="X-1")
    save(school, [app.Student("Dea", T3)], folder="X-2")
    (school / "photos").mkdir()  # a folder without a class list does not count
    assert app.school_summary(school) == (2, 3)
    assert app.count_saved_classes(school) == 2


# ------------------------------------------------------------------ times shown in the app
def test_today_shows_only_the_time():
    assert app.list_time(T2, T2.date()) == "09:42:17"


def test_other_days_show_the_date_too():
    assert app.list_time(T2, date(2026, 10, 2)) == "01.10. 09:42:17"


def test_no_time():
    assert app.list_time(None) == ""
