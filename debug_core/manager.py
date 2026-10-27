"""DebugManager - ядро отладки: порог уровня, список приёмников, отложенное вычисление."""
import threading

from .context import LoggerContext
from .ilogger import ILogger
from .levels import LogLevel
from .record import LogRecord


class DebugManager(ILogger):
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, threshold=LogLevel.DEBUG):
        self._threshold = threshold
        self._sinks = []
        self._lock = threading.Lock()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = DebugManager()
        return cls._instance

    # --- настройка ---
    def add_sink(self, sink):
        with self._lock:
            self._sinks.append(sink)
        return self

    def clear_sinks(self):
        with self._lock:
            self._sinks = []
        return self

    @property
    def threshold(self):
        return self._threshold

    def set_threshold(self, level):
        self._threshold = LogLevel.parse(level) if isinstance(level, str) else level
        return self

    def is_enabled(self, level):
        return level >= self._threshold

    # --- вывод ---
    def log(self, level, template, *args):
        """Отложенное вычисление: пока уровень не прошёл порог,
        ни один аргумент не вычисляется и строка не собирается."""
        if level < self._threshold:
            return
        message = self._render(template, args)
        record = LogRecord(level, message, LoggerContext.snapshot())
        with self._lock:
            sinks = list(self._sinks)
        for sink in sinks:
            sink.write(record)

    @staticmethod
    def _render(template, args):
        if not args:
            return template() if callable(template) else str(template)
        values = [a() if callable(a) else a for a in args]
        text = template() if callable(template) else str(template)
        for value in values:
            text = text.replace("{}", str(value), 1)
        return text

    def debug(self, template, *args):
        # Блок if __debug__ удаляется компилятором при запуске python -O,
        # поэтому в профиле Release тело метода пустое (аналог #if DEBUG).
        if __debug__:
            self.log(LogLevel.DEBUG, template, *args)

    def info(self, template, *args):
        self.log(LogLevel.INFO, template, *args)

    def warn(self, template, *args):
        self.log(LogLevel.WARN, template, *args)

    def error(self, template, *args):
        self.log(LogLevel.ERROR, template, *args)

    def fatal(self, template, *args):
        self.log(LogLevel.FATAL, template, *args)
