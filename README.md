# Эмулятор командной оболочки UNIX

Практическая работа, вариант №12. Эмулятор языка оболочки ОС
с графическим интерфейсом, максимально похожий на работу в командной
строке UNIX-подобной ОС.

Язык реализации — Python 3, интерфейс — `tkinter` (входит в стандартную
библиотеку, сторонние зависимости не нужны).

## Общее описание

Окно эмулятора содержит поле вывода и строку ввода с приглашением
`username@hostname:~$`. Заголовок окна формируется по реальным данным ОС:
`Эмулятор - [username@hostname]`.

Введённая строка разбивается на команду и аргументы по пробелам.
Ввод и вывод каждой команды отображаются в окне, как в терминале.
Сообщения об ошибках выделяются красным цветом.

## Структура проекта

```
src/shell_emulator/
    __main__.py   точка входа
    gui.py        графический интерфейс (tkinter)
    shell.py      парсер и команды (не зависит от GUI)
tests/
    test_shell.py модульные тесты
run.sh            запуск эмулятора и тестов
```

## Команды

| Команда | Описание |
|---|---|
| `ls [-l] [-a] [путь...]` | Заглушка: выводит имя и аргументы. Неизвестный ключ — ошибка `ls: invalid option`. |
| `cd [путь]` | Заглушка: выводит имя и аргумент. Больше одного аргумента — ошибка `cd: too many arguments`. |
| `exit [код]` | Закрывает эмулятор. Код возврата берётся по модулю 256, как в bash. Нечисловой код — ошибка `exit: X: numeric argument required`. |

Неизвестная команда вызывает ошибку `имя: command not found`.

## Сборка и запуск

Нужен Python 3.8+ с поддержкой `tkinter`. Сборка не требуется.

```bash
./run.sh
```

## Тесты

```bash
./run.sh test
```

## Примеры использования

```
zaikov@macbook:~$ ls -l /home
ls: called with arguments: -l /home
zaikov@macbook:~$ ls -z
ls: invalid option -- 'z'
zaikov@macbook:~$ cd /tmp
cd: called with arguments: /tmp
zaikov@macbook:~$ cd a b
cd: too many arguments
zaikov@macbook:~$ pwd
pwd: command not found
zaikov@macbook:~$ exit abc
exit: abc: numeric argument required
zaikov@macbook:~$ exit
exit
```
