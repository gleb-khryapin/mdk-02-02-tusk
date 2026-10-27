"""Интерфейс ILogger."""
from abc import ABC, abstractmethod


class ILogger(ABC):
    @abstractmethod
    def debug(self, template, *args):
        ...

    @abstractmethod
    def info(self, template, *args):
        ...

    @abstractmethod
    def warn(self, template, *args):
        ...

    @abstractmethod
    def error(self, template, *args):
        ...
