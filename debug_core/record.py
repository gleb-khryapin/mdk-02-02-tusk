"""Запись лога - то, что передаётся приёмникам."""
import datetime


class LogRecord:
    __slots__ = ("timestamp", "level", "message", "context")

    def __init__(self, level, message, context):
        self.timestamp = datetime.datetime.now()
        self.level = level
        self.message = message
        self.context = context

    def stamp(self):
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S.") + "%03d" % (self.timestamp.microsecond // 1000)
