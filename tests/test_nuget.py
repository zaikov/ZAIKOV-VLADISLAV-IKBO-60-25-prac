"""Тесты получения зависимостей из репозитория NuGet.

Сеть в тестах не используется: функция загрузки URL подменяется
словарём заранее подготовленных ответов.
"""

import json
import unittest

from depgraph.nuget import (
    ANY_FRAMEWORK, HTTP_NOT_FOUND, NugetClient, NugetError, PackageInfo,
    describe_range, parse_nuspec,
)

INDEX_URL = "https://repo.test/v3/index.json"
BASE_URL = "https://repo.test/flat/"
INDEX = {
    "version": "3.0.0",
    "resources": [
        {"@id": "https://repo.test/search", "@type": "SearchQueryService"},
        {"@id": BASE_URL, "@type": "PackageBaseAddress/3.0.0"},
    ],
}
NUSPEC = b"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>Demo.Package</id>
    <version>2.0.0</version>
    <dependencies>
      <group targetFramework="net8.0">
        <dependency id="Lib.A" version="1.0.0" />
        <dependency id="Lib.B" version="[2.0, 3.0)" />
      </group>
      <group targetFramework=".NETStandard2.0">
        <dependency id="lib.a" version="1.0.0" />
      </group>
      <group targetFramework="net6.0" />
    </dependencies>
  </metadata>
</package>"""


def make_fetch(responses):
    """Создать функцию загрузки, отвечающую из словаря ``responses``.

    Отсутствующий URL даёт ошибку HTTP 404, как настоящий сервер.
    """
    def fetch(url):
        """Вернуть подготовленный ответ для ``url``."""
        if url not in responses:
            raise NugetError(f"{url}: HTTP 404", status=HTTP_NOT_FOUND)
        value = responses[url]
        if isinstance(value, bytes):
            return value
        return json.dumps(value).encode("utf-8")
    return fetch


def make_client(**extra):
    """Создать клиент с индексом служб, версиями и манифестом."""
    responses = {
        INDEX_URL: INDEX,
        BASE_URL + "demo.package/index.json": {
            "versions": ["1.0.0", "2.0.0", "2.1.0-beta"],
        },
        BASE_URL + "demo.package/2.0.0/demo.package.nuspec": NUSPEC,
    }
    responses.update(extra)
    return NugetClient(INDEX_URL, fetch=make_fetch(responses))


class ClientTest(unittest.TestCase):
    """Тесты клиента репозитория."""

    def test_base_address(self):
        """Адрес хранилища берётся из индекса служб."""
        self.assertEqual(make_client().base_address(), BASE_URL)

    def test_latest_stable_version(self):
        """Выбирается последняя стабильная версия, а не beta."""
        self.assertEqual(make_client().latest_version("Demo.Package"), "2.0.0")

    def test_only_prerelease(self):
        """Если стабильных версий нет, берётся последняя предварительная."""
        client = make_client(**{
            BASE_URL + "beta/index.json": {"versions": ["1.0-a", "1.0-b"]},
        })
        self.assertEqual(client.latest_version("Beta"), "1.0-b")

    def test_get_package(self):
        """Имя пакета в запросах приводится к нижнему регистру."""
        package = make_client().get_package("DEMO.Package")
        self.assertEqual(package.package_id, "Demo.Package")
        self.assertEqual(package.version, "2.0.0")
        self.assertEqual(package.unique_dependencies(), ["Lib.A", "Lib.B"])

    def test_package_not_found(self):
        """Неизвестный пакет — понятное сообщение вместо HTTP 404."""
        with self.assertRaisesRegex(NugetError, "'Missing' не найден"):
            make_client().get_package("Missing")

    def test_no_versions(self):
        """Пакет без версий — ошибка."""
        client = make_client(**{BASE_URL + "empty/index.json": {}})
        with self.assertRaisesRegex(NugetError, "нет версий"):
            client.get_package("Empty")

    def test_index_errors(self):
        """Ошибки индекса служб."""
        cases = {
            b"<html></html>": "не является JSON",
            b"[]": "ожидался JSON-объект",
            b'{"versions": []}': "не индекс служб",
            b'{"resources": []}': "нет ресурса PackageBaseAddress",
        }
        for body, message in cases.items():
            with self.subTest(body=body):
                client = NugetClient(
                    INDEX_URL, fetch=make_fetch({INDEX_URL: body})
                )
                with self.assertRaisesRegex(NugetError, message):
                    client.get_package("Demo.Package")

    def test_index_not_found(self):
        """Ошибка сервера при загрузке индекса передаётся дальше."""
        client = NugetClient(INDEX_URL, fetch=make_fetch({}))
        with self.assertRaisesRegex(NugetError, "HTTP 404"):
            client.get_package("Demo.Package")


class NuspecTest(unittest.TestCase):
    """Тесты разбора манифеста .nuspec."""

    def test_groups(self):
        """Зависимости разбираются по целевым платформам."""
        package = parse_nuspec(NUSPEC)
        frameworks = [group.target_framework for group in package.groups]
        self.assertEqual(frameworks, ["net8.0", ".NETStandard2.0", "net6.0"])
        first = package.groups[0].dependencies[1]
        self.assertEqual(first.package_id, "Lib.B")
        self.assertEqual(first.version_range, "[2.0, 3.0)")
        self.assertEqual(package.groups[2].dependencies, [])

    def test_ungrouped_dependencies(self):
        """Старый формат без групп относится к любой платформе."""
        package = parse_nuspec(
            b"<package><metadata><id>Old</id><version>1.0</version>"
            b"<dependencies><dependency id='X' version='1.0'/>"
            b"</dependencies></metadata></package>"
        )
        self.assertEqual(package.groups[0].target_framework, ANY_FRAMEWORK)
        self.assertEqual(package.unique_dependencies(), ["X"])

    def test_no_dependencies(self):
        """Манифест без раздела зависимостей."""
        package = parse_nuspec(
            b"<package><metadata><id>Solo</id><version>1.0</version>"
            b"</metadata></package>"
        )
        self.assertEqual(package.groups, [])

    def test_errors(self):
        """Ошибки формата манифеста."""
        cases = {
            b"<package>": "неверный XML",
            b"<package/>": "нет раздела <metadata>",
            b"<package><metadata><id>A</id></metadata></package>":
                "нет <id> или <version>",
            b"<package><metadata><id>A</id><version>1</version>"
            b"<dependencies><dependency/></dependencies>"
            b"</metadata></package>": "не указан атрибут id",
        }
        for body, message in cases.items():
            with self.subTest(body=body):
                with self.assertRaisesRegex(NugetError, message):
                    parse_nuspec(body)


class HelpersTest(unittest.TestCase):
    """Тесты вспомогательных функций."""

    def test_describe_range(self):
        """Диапазоны версий выводятся в понятном виде."""
        self.assertEqual(describe_range("4.0.0"), ">= 4.0.0")
        self.assertEqual(describe_range("[1.0, 2.0)"), "[1.0, 2.0)")
        self.assertEqual(describe_range(""), "любая версия")

    def test_unique_ignores_case(self):
        """Повторы зависимостей ищутся без учёта регистра."""
        package = parse_nuspec(NUSPEC)
        self.assertIsInstance(package, PackageInfo)
        self.assertEqual(len(package.unique_dependencies()), 2)


if __name__ == "__main__":
    unittest.main()
