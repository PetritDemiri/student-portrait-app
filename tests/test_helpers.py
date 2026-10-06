"""Tests for the parts of foto_nxenesit that don't need a window.

Run from the project folder:  pytest
"""
import random
from datetime import date, datetime

import pytest

import foto_nxenesit as app


@pytest.fixture(autouse=True)
def documents(tmp_path, monkeypatch):
    """Every test gets its own Documents folder, so the tests never touch the real one
    (they also run inside the .exe, on the first start of each version)."""
    monkeypatch.setattr(app, "documents_dir", lambda: tmp_path)
    return tmp_path


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


# ------------------------------------------------------------------ self-check on the first start of a version
def check_result(passed=3, failed=(), skipped=0):
    failed = list(failed)
    return app.CheckResult(total=passed + len(failed) + skipped, passed=passed, failed=failed, skipped=skipped,
                           report="", exit_code=1 if failed else 0, seconds=2.4)


def test_the_exe_checks_each_version_until_it_passes(tmp_path):
    assert app.check_needed(folder=tmp_path, frozen=True)
    app.write_check_record(check_result(failed=["tests/test_helpers.py::test_one"]), folder=tmp_path)
    assert app.check_needed(folder=tmp_path, frozen=True), "a failed check runs again"
    app.write_check_record(check_result(), folder=tmp_path)
    assert not app.check_needed(folder=tmp_path, frozen=True)
    record = tmp_path / app.CHECK_RECORD
    record.write_text(app.read_text(record).replace(f"Versioni: {app.APP_VERSION}", "Versioni: 1.0.0"),
                      encoding="utf-8")
    assert app.check_needed(folder=tmp_path, frozen=True), "a pass of an older version does not count"


def test_a_record_with_only_the_version_is_checked_again(tmp_path):
    (tmp_path / app.CHECK_RECORD).write_text(app.APP_VERSION, encoding="utf-8")  # how 1.3.0 to 1.4.0 wrote it
    assert app.check_needed(folder=tmp_path, frozen=True)


def test_the_record_lists_the_whole_result(tmp_path):
    report = tmp_path / app.CHECK_REPORT
    app.write_check_record(check_result(passed=74, failed=["tests/test_helpers.py::test_one[X-1]"], skipped=1),
                           report=report, folder=tmp_path)
    data = (tmp_path / app.CHECK_RECORD).read_bytes()
    assert data.startswith(b"\xef\xbb\xbf") and b"\r\n" in data, "UTF-8 with BOM and Windows line endings"
    lines = app.read_text(tmp_path / app.CHECK_RECORD).splitlines()
    assert lines[0] == "Kontrolli i programit" and lines[1].startswith("Data: ")
    assert lines[2:10] == [f"Versioni: {app.APP_VERSION}", "Gjendja: Disa kontrolle dështuan", "Gjithsej: 76",
                           "Kaluan: 74", "Dështuan: 1", "  - test_one[X-1]", "U anashkaluan: 1",
                           "Kohëzgjatja: 2,4 sekonda"]
    assert lines[10].startswith("Sistemi: ") and lines[11] == f"Raporti i plotë: {report}"
    fields = app.read_check_record(tmp_path)
    assert fields["Versioni"] == app.APP_VERSION and fields["Dështuan"] == "1" and fields["U anashkaluan"] == "1"


def test_the_record_of_a_passed_check(tmp_path):
    app.write_check_record(check_result(passed=76), folder=tmp_path)
    fields = app.read_check_record(tmp_path)
    assert (fields["Gjendja"], fields["Gjithsej"], fields["Kaluan"], fields["Dështuan"]) == (
        "Të gjitha kaluan", "76", "76", "0")


def test_the_record_of_a_check_that_could_not_run(tmp_path):
    app.write_check_record(RuntimeError("pytest mungon"), folder=tmp_path)
    fields = app.read_check_record(tmp_path)
    assert fields["Gjendja"] == "Kontrolli nuk mund të kryhej"
    assert fields["Arsyeja"] == "RuntimeError: pytest mungon"
    assert app.check_needed(folder=tmp_path, frozen=True)


def test_check_files_live_in_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "documents_dir", lambda: tmp_path)
    assert app.app_data_dir() == tmp_path / "FotoNxenesit"


def test_from_source_only_when_asked(tmp_path):
    assert not app.check_needed(folder=tmp_path, frozen=False)
    assert app.check_needed(force=True, folder=tmp_path, frozen=False)


def test_self_check_counts_tests_and_names_failures(tmp_path):
    (tmp_path / "test_sample.py").write_text(
        "import pytest\n\n\n"
        "def test_passes():\n    assert 1 + 1 == 2\n\n\n"
        "def test_fails():\n    assert 1 + 1 == 3\n\n\n"
        "@pytest.mark.skip(reason='not here')\ndef test_skipped():\n    pass\n", encoding="utf-8")
    progress = []
    result = app.run_self_check(tmp_path, lambda done, total: progress.append((done, total)))
    assert (result.total, result.passed, result.skipped) == (3, 1, 1)
    assert [nodeid.split("::")[-1] for nodeid in result.failed] == ["test_fails"]
    assert not result.ok and result.seconds > 0
    assert progress[0] == (0, 3) and progress[-1] == (3, 3)


# ------------------------------------------------------------------ saved classes: reading and editing
def test_classes_in_school_order():
    classes = ["X-10", "IX-1", "X-2", "VI-3", "XII-1", "X-1", "XI-2"]
    assert sorted(classes, key=app.class_sort_key) == ["VI-3", "IX-1", "X-1", "X-2", "X-10", "XI-2", "XII-1"]


def test_classes_with_numbers_and_words():
    classes = ["10-2", "9-1", "10-10", "Klasa B", "Klasa A"]
    assert sorted(classes, key=app.class_sort_key) == ["Klasa A", "Klasa B", "9-1", "10-2", "10-10"]


def test_list_classes_with_counts(school):
    for name, count in (("X-10", 2), ("X-2", 1), ("IX-1", 3)):
        save(school, [app.Student(f"Nxënës {i}") for i in range(count)], folder=name)
    (school / "fotot").mkdir()  # a folder without a class list
    rows = app.list_classes(school)
    assert [(name, count) for name, _, count, _ in rows] == [("IX-1", 3), ("X-2", 1), ("X-10", 2)]
    assert all(saved is not None for _, _, _, saved in rows)


def test_list_schools_only_with_saved_classes(documents):
    save(documents / "Shkolla B", [app.Student("Arta"), app.Student("Besa")], folder="X-1")
    save(documents / "Shkolla B", [app.Student("Dea")], folder="X-2")
    save(documents / "Shkolla A", [app.Student("Ilir"), app.Student("Jeta")], folder="XI-1")
    (documents / "Fotot e mia").mkdir()
    (documents / "FotoNxenesit" / "kopje").mkdir(parents=True)
    rows = app.list_schools(documents)
    assert [(folder.name, classes, students) for folder, classes, students in rows] == [
        ("Shkolla A", 1, 2), ("Shkolla B", 2, 3)]


def test_insert_keeps_an_alphabetical_list_in_order():
    students = [app.Student("Arta"), app.Student("Dea"), app.Student("Zana")]
    assert [s.name for s in app.insert_student(students, app.Student("Çlirim"))] == ["Arta", "Çlirim", "Dea", "Zana"]


def test_insert_into_a_list_of_one_name_goes_in_alphabetical_place():
    assert [s.name for s in app.insert_student([app.Student("Zana")], app.Student("Besa"))] == ["Besa", "Zana"]


def test_insert_adds_to_the_end_of_photographing_order():
    students = [app.Student("Zana"), app.Student("Arta")]
    assert [s.name for s in app.insert_student(students, app.Student("Besa"))] == ["Zana", "Arta", "Besa"]


def test_backups_live_in_documents(school, documents):
    assert app.backup_path(school, "X-1") == documents / "FotoNxenesit" / "kopje" / "Shkolla" / "X-1.txt"


def test_saving_an_edited_list_keeps_the_version_before_it(school):
    path, _, _ = save(school, [app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2)])
    before = path.read_bytes()
    assert app.save_edited_class(school, "X-1", [app.Student("Arta Gashi", T2), app.Student("Besa")])
    assert app.backup_path(school, "X-1").read_bytes() == before
    assert app.read_text(path).splitlines() == ["1. Arta Gashi – 01.10.2026 09:42:17", "2. Besa", "",
                                                "Gjithsej: 2 nxënës në klasën X-1"]


def test_restoring_swaps_with_the_copy_so_it_can_be_undone(school):
    path, _, _ = save(school, [app.Student("Zana Hoxha", T1)])
    app.save_edited_class(school, "X-1", [app.Student("Dea Rama", T2)])
    assert app.restore_backup(school, "X-1")
    assert app.read_students(path) == [app.Student("Zana Hoxha", T1)]
    assert app.restore_backup(school, "X-1")
    assert app.read_students(path) == [app.Student("Dea Rama", T2)]


def test_no_copy_nothing_to_restore(school):
    save(school, [app.Student("Zana Hoxha", T1)])
    assert not app.restore_backup(school, "X-1")


def test_saving_a_class_over_an_existing_list_keeps_a_copy(school):
    path, _, _ = save(school, [app.Student("Zana Hoxha", T1)])
    before = path.read_bytes()
    save(school, [app.Student("Dea Rama", T2)])  # "Zëvendëso listën"
    assert app.backup_path(school, "X-1").read_bytes() == before


def test_move_a_student_to_another_class(school):
    save(school, [app.Student("Arta Gashi", T1), app.Student("Zana Hoxha", T2)], folder="X-1")
    save(school, [app.Student("Besa", T1), app.Student("Dea", T2)], folder="X-2")
    target = app.move_student(school, "X-1", [app.Student("Zana Hoxha", T2)], "X-2", app.Student("Arta Gashi", T1))
    assert [s.name for s in target] == ["Arta Gashi", "Besa", "Dea"]
    assert app.read_students(school / "X-2" / "X-2.txt")[0] == app.Student("Arta Gashi", T1), "the time moves too"
    assert app.read_students(school / "X-1" / "X-1.txt") == [app.Student("Zana Hoxha", T2)]
    assert app.backup_path(school, "X-1").is_file() and app.backup_path(school, "X-2").is_file()


def test_move_a_student_to_a_new_class(school):
    save(school, [app.Student("Arta"), app.Student("Besa")], folder="X-1")
    target = app.move_student(school, "X-1", [app.Student("Besa")], "X-9", app.Student("Arta"))
    assert target == [app.Student("Arta")]
    assert app.read_text(school / "X-9" / "X-9.txt").splitlines() == ["1. Arta", "", "Gjithsej: 1 nxënës në klasën X-9"]


def test_file_matches_only_the_same_list(school):
    students = [app.Student("Arta Gashi", T2), app.Student("Besa")]
    path, _, _ = save(school, students, alphabetical=False)
    assert app.file_matches(path, app.class_file_lines(students, "X-1"))
    assert not app.file_matches(path, app.class_file_lines(students[:1], "X-1"))
