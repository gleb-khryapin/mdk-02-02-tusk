"""Приёмники логов: консоль, файл с ротацией, аварийный отчёт."""
import json
import os
import shutil
import threading

from .levels import LogLevel


class ISink:
    def write(self, record):
        raise NotImplementedError


class ConsoleSink(ISink):
    """Цветной вывод в терминал."""

    COLORS = {
        LogLevel.DEBUG: "\033[90m",
        LogLevel.INFO: "\033[32m",
        LogLevel.WARN: "\033[33m",
        LogLevel.ERROR: "\033[31m",
        LogLevel.FATAL: "\033[1;37;41m",
    }
    RESET = "\033[0m"

    def __init__(self, colored=True):
        self.colored = colored
        self._lock = threading.Lock()

    def write(self, record):
        ctx = record.context
        line = "[%s] [%s] [%s] [%s] %s" % (
            record.stamp(), record.level.name, ctx.get("req_id", "-"),
            ctx.get("thread", "-"), record.message)
        if self.colored:
            line = self.COLORS.get(record.level, "") + line + self.RESET
        with self._lock:
            print(line, flush=True)


class FileSink(ISink):
    """Пишет в app.log, при достижении лимита архивирует файл.

    json_format=True включает машинный формат для продакшна.
    """

    MAX_BYTES = 1024 * 1024  # 1 МБ

    def __init__(self, path="app.log", json_format=False, max_bytes=None):
        self.path = path
        self.json_format = json_format
        self.max_bytes = max_bytes or self.MAX_BYTES
        self._lock = threading.Lock()
        folder = os.path.dirname(os.path.abspath(path))
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)

    def _format(self, record):
        ctx = record.context
        if self.json_format:
            payload = {
                "timestamp": record.stamp(),
                "level": record.level.name,
                "req_id": ctx.get("req_id", ""),
                "msg": record.message,
            }
            if "user_id" in ctx:
                payload["user_id"] = ctx["user_id"]
            payload["thread"] = ctx.get("thread", "")
            return json.dumps(payload, ensure_ascii=False)
        return "[%s] [%s] [%s] [%s] %s" % (
            record.stamp(), record.level.name, ctx.get("req_id", "-"),
            ctx.get("thread", "-"), record.message)

    def _rotate_if_needed(self, record):
        """Ротация: app.log -> app-ГГГГММДД-ЧЧММСС.log, дальше пишем в пустой файл."""
        if not os.path.exists(self.path):
            return
        if os.path.getsize(self.path) < self.max_bytes:
            return
        root, ext = os.path.splitext(self.path)
        archive = "%s-%s%s" % (root, record.timestamp.strftime("%Y%m%d-%H%M%S"), ext)
        index = 1
        while os.path.exists(archive):
            archive = "%s-%s-%d%s" % (root, record.timestamp.strftime("%Y%m%d-%H%M%S"), index, ext)
            index += 1
        shutil.move(self.path, archive)

    def write(self, record):
        line = self._format(record)
        with self._lock:
            self._rotate_if_needed(record)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")


class CrashReportSink(ISink):
    """Профиль Release: ERROR и FATAL уходят администратору.

    Реальная отправка почты имитируется записью в crash_report.txt.
    """

    def __init__(self, path="crash_report.txt", admin="admin@clinic.local"):
        self.path = path
        self.admin = admin
        self._lock = threading.Lock()

    def write(self, record):
        if record.level < LogLevel.ERROR:
            return
        ctx = record.context
        text = ("Кому: %s\nВремя: %s\nУровень: %s\nЗапрос: %s\nПоток: %s\nСообщение: %s\n%s\n"
                % (self.admin, record.stamp(), record.level.name, ctx.get("req_id", "-"),
                   ctx.get("thread", "-"), record.message, "-" * 60))
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(text)
