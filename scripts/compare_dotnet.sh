#!/bin/sh
# Сравнение с реальным менеджером пакетов: создаёт во временном каталоге
# проект .NET с зависимостью от пакета, выполняет dotnet restore
# и выводит разрешённые пакеты, а затем порядок загрузки depgraph.
# Нужны .NET SDK (команда dotnet) и доступ в интернет.
# Использование: ./scripts/compare_dotnet.sh [ПАКЕТ]
cd "$(dirname "$0")/.." || exit 1
PACKAGE="${1:-Serilog.Sinks.Console}"

if ! command -v dotnet > /dev/null; then
    echo "dotnet не найден: установите .NET SDK" >&2
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1

# Проект сразу для трёх платформ, чтобы увидеть различия между ними.
cat > "$TMP/compare.csproj" <<EOF
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net8.0;netstandard2.0;net462</TargetFrameworks>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="$PACKAGE" Version="*" />
  </ItemGroup>
</Project>
EOF

echo "=== dotnet: пакеты, разрешённые для каждой платформы"
dotnet restore "$TMP" > /dev/null || exit 1
dotnet list "$TMP/compare.csproj" package --include-transitive

echo
echo "=== depgraph: порядок загрузки"
cat > "$TMP/config.toml" <<EOF
package_name = "$PACKAGE"
repository = "https://api.nuget.org/v3/index.json"
test_mode = false
output_file = "graph.svg"
ascii_tree = false
load_order = true
EOF
./run.sh -c "$TMP/config.toml" 2> /dev/null
