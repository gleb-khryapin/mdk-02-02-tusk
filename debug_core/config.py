"""Профили сборки Debug и Release."""
import os

from .levels import LogLevel
from .manager import DebugManager
from .sinks import ConsoleSink, CrashReportSink, FileSink

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")


def _path(name):
    return os.path.normpath(os.path.join(LOG_DIR, name))


def configure(profile=None, json_format=None, max_bytes=None):
    """Debug: уровень DEBUG, консоль + текстовый файл.
    Release: уровень INFO, JSON-файл + отправка ERROR/FATAL администратору."""
    if profile is None:
        profile = "Debug" if __debug__ else "Release"

    log = DebugManager.instance().clear_sinks()
    os.makedirs(LOG_DIR, exist_ok=True)

    if profile == "Debug":
        log.set_threshold(LogLevel.DEBUG)
        log.add_sink(ConsoleSink())
        log.add_sink(FileSink(_path("app.log"),
                              json_format=bool(json_format),
                              max_bytes=max_bytes))
    else:
        log.set_threshold(LogLevel.INFO)
        log.add_sink(ConsoleSink())
        log.add_sink(FileSink(_path("app.log"),
                              json_format=True if json_format is None else bool(json_format),
                              max_bytes=max_bytes))
        log.add_sink(CrashReportSink(_path("crash_report.txt")))
    return log, profile
