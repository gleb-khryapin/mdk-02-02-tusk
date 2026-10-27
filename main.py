"""Демонстрация отладочного ядра: уровни, контекст, отложенное вычисление, ротация."""
import os
import time

from debug_core import DebugManager, LoggerContext, LogLevel, configure
from debug_core.config import LOG_DIR

CALLS = {"expensive": 0}


def expensive_api_call(user_id):
    """Дорогой вызов: считаем, сколько раз его реально выполнили."""
    CALLS["expensive"] += 1
    time.sleep(0.01)
    return 1500.75


def demo_lazy(log):
    log.info("--- проверка отложенного вычисления ---")
    log.set_threshold(LogLevel.INFO)
    CALLS["expensive"] = 0
    log.debug("User {} has balance {}", 42, lambda: expensive_api_call(42))
    log.info("уровень INFO: debug подавлён, дорогой вызов выполнен {} раз", CALLS["expensive"])

    log.set_threshold(LogLevel.DEBUG)
    CALLS["expensive"] = 0
    log.debug("User {} has balance {}", 42, lambda: expensive_api_call(42))
    log.info("уровень DEBUG: дорогой вызов выполнен {} раз", CALLS["expensive"])


def demo_rotation():
    """Ротация при 1 МБ. Для наглядности лимит уменьшен до 8 КБ."""
    log, _ = configure(max_bytes=8 * 1024)
    log.info("--- проверка ротации файла ---")
    for i in range(200):
        log.info("служебная запись номер {} для наполнения файла до лимита", i)
    archives = [f for f in os.listdir(LOG_DIR) if f.startswith("app-")]
    log.info("архивных файлов после ротации: {}", len(archives))


if __name__ == "__main__":
    log, profile = configure()
    LoggerContext.new_request_id()
    LoggerContext.put("user_id", 42)
    log.info("профиль сборки: {} (__debug__={})", profile, __debug__)
    log.debug("это сообщение видно только в профиле Debug")
    if __debug__:
        demo_lazy(log)
    else:
        log.info("профиль Release: вызовы debug исключены из байт-кода")
    log.error("пример ошибки для проверки аварийного отчёта")
    demo_rotation()
    print("\nфайлы логов:", LOG_DIR)
