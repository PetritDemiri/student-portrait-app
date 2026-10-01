"""Tests for the parts of foto_nxenesit that don't need a window.

Run from the project folder:  py -m unittest discover -s tests -v
"""
import random
import sys
import tempfile
import unittest
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


class ClassFiles(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.school = Path(self._tmp.name) / "Shkolla"
        self.school.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_file_format(self):
        path, _, _ = app.save_class(self.school, "X-1", ["Zana Hoxha", "Arta Gashi", "Çlirim Berisha"],
                                    alphabetical=True, merge=False)
        self.assertEqual(path.relative_to(self.school).parts, ("X-1", "X-1.txt"))
        data = path.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM")
        self.assertEqual(data[3:].decode("utf-8"), "Arta Gashi\r\nÇlirim Berisha\r\nZana Hoxha")
        self.assertEqual([p.name for p in path.parent.iterdir()], ["X-1.txt"], "no temporary files left")

    def test_merge_skips_names_already_in_the_file(self):
        app.save_class(self.school, "X-1", ["Zana Hoxha", "Arta Gashi"], alphabetical=True, merge=False)
        _, final, skipped = app.save_class(self.school, "X-1", ["arta gashi", "Besa Krasniqi"],
                                           alphabetical=True, merge=True)
        self.assertEqual(final, ["Arta Gashi", "Besa Krasniqi", "Zana Hoxha"])
        self.assertEqual(skipped, ["arta gashi"])

    def test_merge_in_photographing_order_appends(self):
        app.save_class(self.school, "X-1", ["Zana Hoxha", "Arta Gashi"], alphabetical=False, merge=False)
        _, final, _ = app.save_class(self.school, "X-1", ["Yll Morina"], alphabetical=False, merge=True)
        self.assertEqual(final, ["Zana Hoxha", "Arta Gashi", "Yll Morina"])

    def test_replace(self):
        app.save_class(self.school, "X-1", ["Zana Hoxha"], alphabetical=True, merge=False)
        path, _, _ = app.save_class(self.school, "X-1", ["Dea Rama"], alphabetical=True, merge=False)
        self.assertEqual(app.read_names(path), ["Dea Rama"])

    def test_reads_lists_saved_in_the_old_windows_encoding(self):
        old = self.school / "old.txt"
        old.write_bytes("Ëndrit Çela\r\nArta\r\n\r\n".encode("cp1250"))
        self.assertEqual(app.read_names(old), ["Ëndrit Çela", "Arta"])

    def test_count_saved_classes(self):
        app.save_class(self.school, "X-1", ["Arta"], alphabetical=True, merge=False)
        app.save_class(self.school, "X-2", ["Besa"], alphabetical=True, merge=False)
        (self.school / "photos").mkdir()  # a folder without a class list does not count
        self.assertEqual(app.count_saved_classes(self.school), 2)


if __name__ == "__main__":
    unittest.main()
