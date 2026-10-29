"""Тесты виртуальной файловой системы и команды vfs-init."""

import os
import tempfile
import unittest

from shell_emulator.shell import Shell, ShellError
from shell_emulator.vfs import VfsDir, VfsError, read_vfs, write_vfs

# Папка vfs/ с примерами лежит в корне проекта, рядом с tests/.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_DIR, "vfs")
HEADER = "path,type,content\n"
MIN_DEPTH = 3


class VfsTestCase(unittest.TestCase):
    """Базовый класс: временный каталог для CSV-файлов."""

    def setUp(self):
        """Создать временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make_csv(self, text, name="vfs.csv"):
        """Записать CSV-файл во временный каталог и вернуть путь к нему."""
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path


class ReadVfsTest(VfsTestCase):
    """Тесты загрузки VFS из CSV."""

    def test_header_only(self):
        """Файл только с заголовком — пустая VFS."""
        vfs = read_vfs(self.make_csv(HEADER))
        self.assertEqual(vfs.stats(), (0, 0, 0))

    def test_nested_and_base64(self):
        """Вложенные элементы и содержимое в base64."""
        vfs = read_vfs(self.make_csv(
            HEADER + "/a,dir,\n/a/b,dir,\n/a/b/c.txt,file,SGVsbG8=\n"
        ))
        file = vfs.root.children["a"].children["b"].children["c.txt"]
        self.assertEqual(file.data, b"Hello")
        self.assertEqual(vfs.stats(), (2, 1, 3))

    def test_order_does_not_matter(self):
        """Вложенный элемент может идти в файле раньше родителя."""
        vfs = read_vfs(self.make_csv(HEADER + "/a/f,file,\n/a,dir,\n"))
        self.assertIsInstance(vfs.root.children["a"], VfsDir)

    def test_samples(self):
        """Примеры из папки vfs/ загружаются без ошибок."""
        for name in ("minimal.csv", "several.csv", "deep.csv"):
            with self.subTest(name=name):
                read_vfs(os.path.join(SAMPLES_DIR, name))
        deep = read_vfs(os.path.join(SAMPLES_DIR, "deep.csv"))
        self.assertGreaterEqual(deep.stats()[2], MIN_DEPTH)

    def test_invalid_samples(self):
        """Каждый пример из vfs/invalid/ вызывает ошибку загрузки."""
        invalid_dir = os.path.join(SAMPLES_DIR, "invalid")
        for name in sorted(os.listdir(invalid_dir)):
            with self.subTest(name=name):
                with self.assertRaises(VfsError):
                    read_vfs(os.path.join(invalid_dir, name))

    def test_errors(self):
        """Сообщения об ошибках формата."""
        cases = {
            "bad,header\n": "invalid header",
            HEADER + "/a,file\n": "expected 3 columns",
            HEADER + "/a,link,\n": "unknown type 'link'",
            HEADER + "/a,file,@@@\n": "invalid base64",
            HEADER + "/a/b,file,\n": "parent directory /a not found",
            HEADER + "/a,file,\n/a/b,file,\n": "parent directory /a",
            HEADER + "/a,dir,\n/a,dir,\n": "duplicate path /a",
            HEADER + "a,dir,\n": "invalid path 'a'",
            HEADER + "/a//b,dir,\n": "invalid path",
            HEADER + "/a,dir,SGVsbG8=\n": "directory /a has content",
        }
        for text, message in cases.items():
            with self.subTest(text=text):
                with self.assertRaisesRegex(VfsError, message):
                    read_vfs(self.make_csv(text))

    def test_missing_file(self):
        """Отсутствующий файл — ошибка с путём к файлу."""
        missing = os.path.join(self.tmp.name, "missing.csv")
        with self.assertRaisesRegex(VfsError, "missing.csv: file not found"):
            read_vfs(missing)

    def test_write_and_read_back(self):
        """После сохранения и повторной загрузки VFS не меняется."""
        source = os.path.join(SAMPLES_DIR, "several.csv")
        copy = os.path.join(self.tmp.name, "copy.csv")
        write_vfs(read_vfs(source), copy)
        original = read_vfs(source).root.children["data.bin"].data
        restored = read_vfs(copy).root.children["data.bin"].data
        self.assertEqual(restored, original)


class VfsInitTest(VfsTestCase):
    """Тесты загрузки VFS в оболочку и команды vfs-init."""

    def setUp(self):
        """Создать оболочку и CSV-файл с одним каталогом."""
        super().setUp()
        self.shell = Shell()
        self.path = self.make_csv(HEADER + "/home,dir,\n")

    def test_load(self):
        """Загруженная VFS становится текущей."""
        self.shell.load_vfs(self.path)
        self.assertIn("home", self.shell.vfs.root.children)

    def test_failed_load_keeps_default(self):
        """При ошибке загрузки остаётся VFS по умолчанию."""
        with self.assertRaises(VfsError):
            self.shell.load_vfs(os.path.join(self.tmp.name, "no.csv"))
        self.assertEqual(self.shell.vfs.root.children, {})

    def test_vfs_init_clears_file(self):
        """vfs-init очищает VFS в памяти и CSV-файл."""
        self.shell.load_vfs(self.path)
        output = self.shell.execute("vfs-init")
        self.assertIn("cleared", output)
        self.assertEqual(self.shell.vfs.root.children, {})
        with open(self.path, encoding="utf-8") as file:
            self.assertEqual(file.read(), HEADER)

    def test_vfs_init_without_file(self):
        """Без файла VFS vfs-init сбрасывает только память."""
        output = self.shell.execute("vfs-init")
        self.assertEqual(output, "vfs-init: VFS reset to default")

    def test_vfs_init_with_args(self):
        """vfs-init не принимает аргументов."""
        with self.assertRaisesRegex(ShellError, "too many arguments"):
            self.shell.execute("vfs-init extra")


if __name__ == "__main__":
    unittest.main()
