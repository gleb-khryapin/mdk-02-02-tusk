"""BookingService: проверка суточной квоты комнаты.

unsafe=True воспроизводит исходную ошибку (неатомарная пара "проверил - записал"),
unsafe=False - исправленный вариант с мьютексом.
"""
from debug_core import DebugManager, LoggerContext, LogLevel, trace

QUOTA_PER_DAY = 5


class QuotaExceeded(Exception):
    pass


class BookingService:
    def __init__(self, store, unsafe=True, lock=None):
        self.store = store
        self.unsafe = unsafe
        self.log = DebugManager.instance()
        if lock is None:
            import threading
            lock = threading.Lock()
        self._lock = lock

    @trace
    def book(self, room, day, user_id):
        LoggerContext.put("user_id", user_id)
        if self.unsafe:
            return self._book_unsafe(room, day, user_id)
        return self._book_safe(room, day, user_id)

    # --- версия с ошибкой ---
    def _book_unsafe(self, room, day, user_id):
        count = self.store.count(room, day)
        if __debug__:
            self.log.debug("проверка квоты: комната={} день={} занято={} лимит={}",
                           room, day, count, QUOTA_PER_DAY)
        if count < QUOTA_PER_DAY:
            if __debug__:
                self.log.debug("проверка пройдена, записываю бронь пользователя {}", user_id)
            booking = self.store.save({"room": room, "day": day, "user": user_id})
            self.log.info("пользователь {} забронировал комнату {}", user_id, room)
            return booking
        self.log.warn("отказ: квота комнаты {} на {} исчерпана", room, day)
        raise QuotaExceeded(room)

    # --- исправленная версия ---
    def _book_safe(self, room, day, user_id):
        with self._lock:  # критическая секция: проверка и запись неразделимы
            count = self.store.count(room, day)
            if __debug__:
                self.log.debug("проверка квоты под мьютексом: занято={} лимит={}", count, QUOTA_PER_DAY)
            if count >= QUOTA_PER_DAY:
                self.log.warn("отказ: квота комнаты {} на {} исчерпана", room, day)
                raise QuotaExceeded(room)
            booking = self.store.save({"room": room, "day": day, "user": user_id})
        self.log.info("пользователь {} забронировал комнату {}", user_id, room)
        return booking
