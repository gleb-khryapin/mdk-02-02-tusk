"""Уровни логирования и их порядок."""
from enum import IntEnum


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50

    @classmethod
    def parse(cls, name):
        return cls[str(name).upper()]
