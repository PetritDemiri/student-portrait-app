"""Tests for the parts of foto_nxenesit that don't need a window.

Run from the project folder:  py -m unittest discover -s tests -v
"""
import random
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import foto_nxenesit as app  # noqa: E402


class AlbanianOrder(unittest.TestCase):
    def assertOrder(self, *names):
        """The names must come out in exactly this order, whatever order they go in."""
        names = list(names)
        for seed in range(5):
            shuffled = names[:]
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(app.sort_albanian(shuffled), names)

    def test_digraphs_are_single_letters(self):
        for names in [("Syla", "Shala"), ("Tushi", "Thaçi"), ("Lushaku", "Llapashtica"), ("Zymberi", "Zhuri"),
                      ("Nora", "Nuhiu", "Njomza"), ("Rama", "Rugova", "Rrahmani"), ("Dushi", "Dhurata"),
                      ("Xoxa", "Xhaka"), ("Gashi", "Gzimi", "Gjergji")]:
            with self.subTest(names=names):
                self.assertOrder(*names)

    def test_letters_inside_words(self):
        for names in [("Kaçaku", "Kadriu"), ("Hasani", "Hasi", "Hashani"), ("Mazreku", "Mehmeti", "Mëhmeti"),
                      ("Morina", "Mulaku", "Mulliqi"), ("Bekteshi", "Beqiri", "Berisha"),
                      ("Erza", "Ëndrit", "Fatmir"), ("Cufaj", "Çlirim", "Dardan")]:
            with self.subTest(names=names):
                self.assertOrder(*names)

    def test_whole_alphabet(self):
        self.assertOrder(
            "Agon", "Arta", "Besnik", "Blerina", "Çlirim", "Dardan", "Donika", "Dhurata", "Elira", "Ëndrit",
            "Fjolla", "Gentrit", "Gresa", "Gjergj", "Hana", "Ilir", "Jeton", "Kaltrina", "Liridon", "Lluka",
            "Mimoza", "Nora", "Njomza", "Orges", "Petrit", "Qendresa", "Rina", "Rrezon", "Sara", "Syzana",
            "Shqipe", "Teuta", "Thëllëza", "Uran", "Valon", "Xeni", "Xhemile", "Yll", "Zana", "Zhaneta")

    def test_word_by_word(self):
        self.assertOrder("Ana Zeka", "Anabela Berisha")
        self.assertOrder("Arta", "Arta Krasniqi", "Arta Mustafa")
        self.assertOrder("Ana Berisha", "Ana Gashi", "Ana-Maria Gashi")

    def test_letters_from_other_languages(self):
        self.assertOrder("Cufaj", "Čolić", "Çlirim")
        self.assertOrder("Valon", "William", "Xeni")
        self.assertOrder("Syzana", "Šehu", "Shqipe")
        self.assertOrder("Zana", "Žarko", "Zhaneta")

    def test_case_and_decomposed_letters(self):
        self.assertEqual(app.sort_albanian(["DHURATA", "Dea", "dardan"]), ["dardan", "Dea", "DHURATA"])
        decomposed = "E\u0308ndrit"  # E followed by a combining diaeresis
        self.assertEqual(app.sort_albanian([decomposed, "Fisnik", "Erza"]), ["Erza", decomposed, "Fisnik"])


class Names(unittest.TestCase):
    def test_clean_name(self):
        cases = {"  arta   krasniqi ": "Arta Krasniqi", "ARTA KRASNIQI": "ARTA KRASNIQI",
                 "ëndrit berisha": "Ëndrit Berisha", "arta-maria gashi": "Arta-Maria Gashi",
                 "çlirim hoxha": "Çlirim Hoxha", "dhurata": "Dhurata", "   ": "", "E\u0308ndrit": "Ëndrit"}
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(app.clean_name(raw), expected)

    def test_folder_name(self):
        cases = {'SHFMU "Naim Frashëri"': "SHFMU “Naim Frashëri”", "X/1": "X-1", "XII\\3": "XII-3",
                 "X-1": "X-1", "  X  -  1 ": "X - 1", "Shkolla.": "Shkolla", "a<b>c|d?e*": "abcde",
                 "CON": "_CON", "nul.txt": "_nul.txt", "...": "", "": ""}
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(app.folder_name(raw), expected)


T1 = datetime(2026, 10, 1, 9, 40, 2)
T2 = datetime(2026, 10, 1, 9, 42, 17)
T3 = datetime(2026, 10, 1, 9, 44, 51)


class ClassFiles(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.school = Path(self._tmp.name) / "Shkolla"
        self.school.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def save(self, students, alphabetical=True, merge=False, folder="X-1"):
        return app.save_class(self.school, folder, students, alphabetical=alphabetical, merge=merge)

    def test_alphabetical_file_is_numbered_with_times_and_total(self):
        path, _, _ = self.save([app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2),
                                app.Student("Çlirim Berisha", T3)])
        self.assertEqual(path.relative_to(self.school).parts, ("X-1", "X-1.txt"))
        data = path.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM")
        self.assertEqual(data[3:].decode("utf-8"),
                         "1. Arta Gashi – 01.10.2026 09:42:17\r\n"
                         "2. Çlirim Berisha – 01.10.2026 09:44:51\r\n"
                         "3. Zana Hoxha – 01.10.2026 09:40:02\r\n"
                         "\r\n"
                         "Gjithsej: 3 nxënës në klasën X-1")
        self.assertEqual([p.name for p in path.parent.iterdir()], ["X-1.txt"], "no temporary files left")

    def test_photographing_order_is_numbered_too(self):
        path, _, _ = self.save([app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2)], alphabetical=False)
        lines = app.read_text(path).splitlines()
        self.assertEqual(lines[:2], ["1. Zana Hoxha – 01.10.2026 09:40:02", "2. Arta Gashi – 01.10.2026 09:42:17"])
        self.assertEqual(lines[-1], "Gjithsej: 2 nxënës në klasën X-1")

    def test_file_reads_back_the_same_students(self):
        students = [app.Student("Arta Gashi", T2), app.Student("Ana - Maria Krasniqi", T3), app.Student("Besa", None)]
        path, final, _ = self.save(students, alphabetical=False)
        self.assertEqual(app.read_students(path), final)

    def test_merge_skips_names_already_in_the_file_and_recounts(self):
        self.save([app.Student("Zana Hoxha", T1), app.Student("Arta Gashi", T2)])
        path, final, skipped = self.save([app.Student("arta gashi", T3), app.Student("Besa Krasniqi", T3)],
                                         merge=True)
        self.assertEqual([s.name for s in final], ["Arta Gashi", "Besa Krasniqi", "Zana Hoxha"])
        self.assertEqual(final[0].taken, T2, "the time already in the file is kept")
        self.assertEqual([s.name for s in skipped], ["arta gashi"])
        self.assertEqual(app.read_text(path).splitlines()[-1], "Gjithsej: 3 nxënës në klasën X-1")

    def test_merge_with_a_list_saved_by_version_1_0_0(self):
        folder = self.school / "X-1"
        folder.mkdir()
        (folder / "X-1.txt").write_bytes("\ufeffZana Hoxha\r\nArta Gashi".encode("utf-8"))
        path, final, _ = self.save([app.Student("Yll Morina", T3)], alphabetical=False, merge=True)
        self.assertEqual(final, [app.Student("Zana Hoxha"), app.Student("Arta Gashi"), app.Student("Yll Morina", T3)])
        self.assertEqual(app.read_text(path).splitlines()[:3],
                         ["1. Zana Hoxha", "2. Arta Gashi", "3. Yll Morina – 01.10.2026 09:44:51"])

    def test_replace(self):
        self.save([app.Student("Zana Hoxha", T1)])
        path, _, _ = self.save([app.Student("Dea Rama", T2)])
        self.assertEqual(app.read_students(path), [app.Student("Dea Rama", T2)])

    def test_parsing_ignores_numbers_and_total_but_keeps_names_with_dashes(self):
        text = ("1. Ana - Maria Gashi – 01.10.2026 09:42:17\n"
                "2) Besa Krasniqi - 30.09.2026 14:05\n"
                "Dea Rama\n\n"
                "Gjithsej: 3 nxënës në klasën X-1\n")
        self.assertEqual(app.parse_students(text), [
            app.Student("Ana - Maria Gashi", T2),
            app.Student("Besa Krasniqi", datetime(2026, 9, 30, 14, 5)),
            app.Student("Dea Rama")])

    def test_reads_lists_saved_in_the_old_windows_encoding(self):
        old = self.school / "old.txt"
        old.write_bytes("Ëndrit Çela\r\nArta\r\n\r\n".encode("cp1250"))
        self.assertEqual([s.name for s in app.read_students(old)], ["Ëndrit Çela", "Arta"])

    def test_school_summary(self):
        self.save([app.Student("Arta", T1), app.Student("Besa", T2)], folder="X-1")
        self.save([app.Student("Dea", T3)], folder="X-2")
        (self.school / "photos").mkdir()  # a folder without a class list does not count
        self.assertEqual(app.school_summary(self.school), (2, 3))
        self.assertEqual(app.count_saved_classes(self.school), 2)


class TimesInTheApp(unittest.TestCase):
    def test_today_shows_only_the_time(self):
        self.assertEqual(app.list_time(T2, T2.date()), "09:42:17")

    def test_other_days_show_the_date_too(self):
        self.assertEqual(app.list_time(T2, date(2026, 10, 2)), "01.10. 09:42:17")

    def test_no_time(self):
        self.assertEqual(app.list_time(None), "")


if __name__ == "__main__":
    unittest.main()
