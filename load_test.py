"""Имитация нагрузки: 10 потоков одновременно бронируют одну комнату."""
import argparse
import threading

from booking import BookingService, BookingStore, QuotaExceeded, QUOTA_PER_DAY
from debug_core import DebugManager, LoggerContext, configure

ROOM = 101
DAY = "2026-10-27"
THREADS = 10


def worker(service, user_id, results, barrier):
    LoggerContext.new_request_id()
    LoggerContext.put("user_id", user_id)
    barrier.wait()  # стартуем одновременно - так гонка воспроизводится устойчиво
    try:
        service.book(ROOM, DAY, user_id)
        results.append(("ok", user_id))
    except QuotaExceeded:
        results.append(("deny", user_id))
    finally:
        LoggerContext.clear()


def run(unsafe, level="DEBUG"):
    log, profile = configure()
    log.set_threshold(level)
    store = BookingStore()
    service = BookingService(store, unsafe=unsafe)
    results = []
    barrier = threading.Barrier(THREADS)

    log.info("=== запуск нагрузки: потоков={} режим={} профиль={} ===",
             THREADS, "с ошибкой" if unsafe else "исправленный", profile)

    threads = [threading.Thread(target=worker, args=(service, 100 + i, results, barrier),
                                name="Thread-%d" % (i + 1)) for i in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    saved = len(store.all())
    ok = sum(1 for r in results if r[0] == "ok")
    deny = sum(1 for r in results if r[0] == "deny")
    log.info("итог: сохранено броней={} лимит={} подтверждено={} отказов={}",
             saved, QUOTA_PER_DAY, ok, deny)
    if saved > QUOTA_PER_DAY:
        log.error("нарушение квоты: записано {} броней при лимите {} - гонка потоков",
                  saved, QUOTA_PER_DAY)
    else:
        log.info("квота соблюдена")
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Нагрузочная проверка квоты бронирования")
    parser.add_argument("--fixed", action="store_true", help="запустить исправленную версию")
    parser.add_argument("--level", default="DEBUG", help="порог логирования")
    args = parser.parse_args()
    run(unsafe=not args.fixed, level=args.level)
