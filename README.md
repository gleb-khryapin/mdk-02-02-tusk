# Система отладочных классов для модуля бронирования

## Этапы работы

- `legacy_service/` - этап 1: исходная учебная задача (сервис бронирования
  переговорных комнат без логирования, с магическими числами, отладкой через
  print и скрытой ошибкой проверки квоты);
- корень репозитория - этап 2: система отладочных классов, локализация и
  исправление состязания потоков, профили Debug и Release, функциональные тесты.

## Запуск

| Команда | Что делает |
|---|---|
| `python main.py` | профиль Debug: уровни, контекст, отложенное вычисление, ротация |
| `python -O main.py` | профиль Release: JSON-логи, debug исключён, отчёт администратору |
| `python load_test.py` | 10 потоков, версия с ошибкой - квота нарушается |
| `python load_test.py --fixed` | та же нагрузка с мьютексом - квота соблюдается |
| `python check_release.py` / `python -O check_release.py` | показывает, что в Release вызова debug нет в байт-коде |

Логи пишутся в папку `logs`: `app.log`, архивы `app-ГГГГММДД-ЧЧММСС.log`, `crash_report.txt`.

## Состав

- `debug_core/ilogger.py` - интерфейс ILogger (debug, info, warn, error)
- `debug_core/context.py` - LoggerContext, метаданные запроса по потокам
- `debug_core/manager.py` - DebugManager: порог уровня, приёмники, отложенное вычисление
- `debug_core/sinks.py` - ConsoleSink, FileSink (текст/JSON, ротация 1 МБ), CrashReportSink
- `debug_core/trace.py` - декоратор трассировки входов в функции
- `debug_core/config.py` - профили сборки Debug и Release
- `booking/` - сервис бронирования и симулятор БД
- `load_test.py` - нагрузочная проверка квоты
