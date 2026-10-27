"""Трассировка входов в функции. В профиле Release (python -O) исключается целиком."""
import functools

from .levels import LogLevel
from .manager import DebugManager


def trace(func):
    """В Debug оборачивает функцию, в Release возвращает её без изменений.

    __debug__ равен False при запуске python -O, и ветка с обёрткой
    не попадает в исполняемый байт-код - это аналог #if DEBUG.
    """
    if not __debug__:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        log = DebugManager.instance()
        if log.is_enabled(LogLevel.DEBUG):
            log.debug("-> вход в {} args={}", func.__qualname__, lambda: args[1:])
        result = func(*args, **kwargs)
        if log.is_enabled(LogLevel.DEBUG):
            log.debug("<- выход из {} результат={}", func.__qualname__, result)
        return result

    return wrapper
