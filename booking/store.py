"""Симулятор БД: хранит брони и намеренно медленно отвечает."""
import threading
import time


class BookingStore:
    def __init__(self, latency=0.002):
        self._rows = []
        self._latency = latency
        self._lock = threading.Lock()

    def count(self, room, day):
        time.sleep(self._latency)  # имитация обращения к БД
        with self._lock:
            return sum(1 for r in self._rows if r["room"] == room and r["day"] == day)

    def save(self, booking):
        time.sleep(self._latency)
        with self._lock:
            self._rows.append(booking)
        return booking

    def all(self):
        with self._lock:
            return list(self._rows)

    def clear(self):
        with self._lock:
            self._rows = []
