"""Получение прямых зависимостей пакета из репозитория NuGet (API v3).

Используется только стандартная библиотека Python, без менеджеров
пакетов и сторонних библиотек. Данные получаются тремя запросами:

1. индекс служб (``repository`` из конфигурации) — в нём находится
   адрес хранилища пакетов, ресурса ``PackageBaseAddress/3.0.0``;
2. ``{хранилище}/{id}/index.json`` — список версий пакета;
3. ``{хранилище}/{id}/{версия}/{id}.nuspec`` — манифест пакета в XML,
   в разделе ``<dependencies>`` которого перечислены прямые зависимости.

``PRERELEASE_MARK`` — признак предварительной версии (6.1.0-dev-02308),
``ANY_FRAMEWORK`` — платформа для зависимостей, записанных в манифесте
без группы.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from xml.etree import ElementTree

PACKAGE_BASE_TYPE = "PackageBaseAddress/3.0.0"
REQUEST_TIMEOUT = 30
USER_AGENT = "depgraph/0.2"
HTTP_NOT_FOUND = 404
PRERELEASE_MARK = "-"
ANY_FRAMEWORK = "any"


class NugetError(Exception):
    """Ошибка получения данных из репозитория NuGet.

    ``status`` — код ответа HTTP, если ошибку вернул сервер.
    """

    def __init__(self, message, status=None):
        """Создать исключение с сообщением и кодом HTTP."""
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Dependency:
    """Прямая зависимость: имя пакета и допустимые версии."""

    package_id: str
    version_range: str


@dataclass
class DependencyGroup:
    """Зависимости пакета для одной целевой платформы .NET."""

    target_framework: str
    dependencies: list = field(default_factory=list)


@dataclass
class PackageInfo:
    """Пакет NuGet: имя, версия и группы прямых зависимостей."""

    package_id: str
    version: str
    groups: list = field(default_factory=list)

    def unique_dependencies(self):
        """Вернуть имена зависимостей всех групп без повторов.

        Имена пакетов NuGet не зависят от регистра, поэтому повторы
        ищутся без учёта регистра; порядок — по первому появлению.
        """
        names = {}
        for group in self.groups:
            for dependency in group.dependencies:
                key = dependency.package_id.lower()
                names.setdefault(key, dependency.package_id)
        return list(names.values())


def fetch_url(url):
    """Загрузить содержимое по URL и вернуть его в виде байтов.

    :raises NugetError: при ошибке сети или ответе сервера с ошибкой.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as reply:
            return reply.read()
    except urllib.error.HTTPError as error:
        raise NugetError(
            f"{url}: сервер вернул ошибку HTTP {error.code} {error.reason}",
            status=error.code,
        ) from None
    except urllib.error.URLError as error:
        raise NugetError(
            f"{url}: не удалось подключиться: {error.reason}"
        ) from None
    except TimeoutError:
        raise NugetError(f"{url}: превышено время ожидания ответа") from None


class NugetClient:
    """Клиент репозитория NuGet по адресу индекса служб."""

    def __init__(self, index_url, fetch=fetch_url):
        """Создать клиент.

        :param index_url: URL индекса служб, например
            ``https://api.nuget.org/v3/index.json``.
        :param fetch: функция загрузки URL; в тестах подменяется,
            чтобы не обращаться к сети.
        """
        self.index_url = index_url
        self._fetch = fetch
        self._base_address = None

    def base_address(self):
        """Вернуть адрес хранилища пакетов из индекса служб.

        Индекс служб загружается один раз, адрес запоминается.
        """
        if self._base_address is None:
            index = parse_json(self._fetch(self.index_url), self.index_url)
            self._base_address = find_resource(
                index, PACKAGE_BASE_TYPE, self.index_url
            )
        return self._base_address

    def versions(self, package_id):
        """Вернуть список версий пакета по возрастанию.

        :raises NugetError: если пакет не найден или версий нет.
        """
        url = f"{self.base_address()}{package_id.lower()}/index.json"
        try:
            data = self._fetch(url)
        except NugetError as error:
            if error.status == HTTP_NOT_FOUND:
                raise NugetError(
                    f"пакет '{package_id}' не найден в репозитории"
                ) from None
            raise
        versions = parse_json(data, url).get("versions")
        if not isinstance(versions, list) or not versions:
            raise NugetError(f"у пакета '{package_id}' нет версий")
        return versions

    def latest_version(self, package_id):
        """Вернуть последнюю стабильную версию пакета.

        Хранилище отдаёт версии отсортированными по возрастанию.
        Если стабильных версий нет, возвращается последняя
        предварительная.
        """
        versions = self.versions(package_id)
        stable = [item for item in versions if PRERELEASE_MARK not in item]
        return (stable or versions)[-1]

    def get_package(self, package_id, version=None):
        """Загрузить манифест пакета и его прямые зависимости.

        :param package_id: имя пакета.
        :param version: версия; по умолчанию последняя стабильная.
        :return: объект :class:`PackageInfo`.
        """
        if version is None:
            version = self.latest_version(package_id)
        lower_id = package_id.lower()
        url = (
            f"{self.base_address()}{lower_id}/{version.lower()}/"
            f"{lower_id}.nuspec"
        )
        return parse_nuspec(self._fetch(url), url)


def parse_json(data, url):
    """Разобрать ответ сервера в формате JSON.

    :raises NugetError: если ответ не является JSON-объектом.
    """
    try:
        value = json.loads(data)
    except ValueError:
        raise NugetError(f"{url}: ответ сервера не является JSON") from None
    if not isinstance(value, dict):
        raise NugetError(f"{url}: ожидался JSON-объект")
    return value


def find_resource(index, resource_type, url):
    """Найти в индексе служб адрес ресурса заданного типа.

    Адрес используется как префикс других адресов, поэтому
    при необходимости дополняется символом «/».
    """
    resources = index.get("resources")
    if not isinstance(resources, list):
        raise NugetError(f"{url}: это не индекс служб NuGet v3")
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        if resource.get("@type") == resource_type:
            address = str(resource.get("@id", ""))
            return address if address.endswith("/") else address + "/"
    raise NugetError(f"{url}: в индексе служб нет ресурса {resource_type}")


def parse_nuspec(data, url=".nuspec"):
    """Разобрать манифест пакета ``.nuspec``.

    :param data: содержимое манифеста (XML).
    :param url: адрес манифеста для сообщений об ошибках.
    :return: объект :class:`PackageInfo`.
    :raises NugetError: если XML неверен или нет нужных элементов.
    """
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise NugetError(f"{url}: неверный XML: {error}") from None
    metadata = find_child(root, "metadata")
    if metadata is None:
        raise NugetError(f"{url}: в манифесте нет раздела <metadata>")
    package_id = find_text(metadata, "id")
    version = find_text(metadata, "version")
    if not package_id or not version:
        raise NugetError(f"{url}: в манифесте нет <id> или <version>")
    dependencies = find_child(metadata, "dependencies")
    groups = [] if dependencies is None else parse_groups(dependencies, url)
    return PackageInfo(package_id, version, groups)


def parse_groups(element, url):
    """Разобрать раздел ``<dependencies>`` манифеста.

    Зависимости бывают сгруппированы по платформам (``<group>``)
    или перечислены сразу (старый формат) — тогда они относятся
    к любой платформе.
    """
    groups = []
    ungrouped = DependencyGroup(ANY_FRAMEWORK)
    for child in element:
        name = local_name(child)
        if name == "group":
            framework = child.get("targetFramework", ANY_FRAMEWORK)
            items = [
                parse_dependency(item, url)
                for item in child if local_name(item) == "dependency"
            ]
            groups.append(DependencyGroup(framework, items))
        elif name == "dependency":
            ungrouped.dependencies.append(parse_dependency(child, url))
    if ungrouped.dependencies:
        groups.insert(0, ungrouped)
    return groups


def parse_dependency(element, url):
    """Разобрать элемент ``<dependency id="..." version="..."/>``."""
    package_id = element.get("id", "").strip()
    if not package_id:
        raise NugetError(f"{url}: у зависимости не указан атрибут id")
    return Dependency(package_id, element.get("version", "").strip())


def local_name(element):
    """Вернуть имя элемента XML без пространства имён.

    Пространство имён .nuspec зависит от версии схемы, поэтому
    элементы сравниваются только по локальному имени.
    """
    return element.tag.rsplit("}", 1)[-1]


def find_child(element, name):
    """Найти первый дочерний элемент с локальным именем ``name``."""
    for child in element:
        if local_name(child) == name:
            return child
    return None


def find_text(element, name):
    """Вернуть текст дочернего элемента или пустую строку."""
    child = find_child(element, name)
    if child is None or child.text is None:
        return ""
    return child.text.strip()
