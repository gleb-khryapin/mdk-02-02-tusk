"""Функциональные тесты: проверяем поведение системы по требованиям, не заглядывая внутрь."""
import json
import os
import shutil
import tempfile
import threading
import unittest

from booking import BookingService, BookingStore, QuotaExceeded, QUOTA_PER_DAY
from debug_core import DebugManager, LoggerContext, LogLevel
from debug_core.sinks import CrashReportSink, FileSink

ROOM, DAY, THREADS = 101, "2026-10-27", 10


class MemorySink:
    """Приёмник для тестов: копит записи в памяти."""

    def __init__(self):
        self.records = []

    def write(self, record):
        self.records.append(record)

    def levels(self):
        return [r.level for r in self.records]


class LoggerFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.sink = MemorySink()
        self.log = DebugManager.instance().clear_sinks().add_sink(self.sink)
        self.log.set_threshold(LogLevel.DEBUG)
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        self.log.clear_sinks()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_threshold_filters_lower_levels(self):
        """При пороге INFO сообщения DEBUG в журнал не попадают."""
        self.log.set_threshold(LogLevel.INFO)
        self.log.log(LogLevel.DEBUG, "скрыто")
        self.log.info("видно")
        self.assertEqual(self.sink.levels(), [LogLevel.INFO])

    def test_arguments_are_not_evaluated_below_threshold(self):
        """Аргументы не вычисляются, если уровень ниже порога."""
        calls = []
        self.log.set_threshold(LogLevel.INFO)
        self.log.log(LogLevel.DEBUG, "balance {}", lambda: calls.append(1))
        self.assertEqual(len(calls), 0)
        self.log.set_threshold(LogLevel.DEBUG)
        self.log.log(LogLevel.DEBUG, "balance {}", lambda: (calls.append(1), 10)[1])
        self.assertEqual(len(calls), 1)

    def test_text_format_matches_specification(self):
        """Строка файла имеет вид [дата] [уровень] [req_id] [поток] сообщение."""
        path = os.path.join(self.tmp, "app.log")
        self.log.clear_sinks().add_sink(FileSink(path))
        LoggerContext.put("req_id", "req-abc-123")
        self.log.info("User {} booked room {}", 42, 101)
        with open(path, encoding="utf-8") as fh:
            line = fh.read().strip()
        self.assertRegex(line, r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\] \[INFO\] "
                               r"\[req-abc-123\] \[.+\] User 42 booked room 101$")

    def test_json_format_contains_required_fields(self):
        """В формате JSON присутствуют все поля из требований."""
        path = os.path.join(self.tmp, "app.log")
        self.log.clear_sinks().add_sink(FileSink(path, json_format=True))
        LoggerContext.put("req_id", "req-abc-123")
        LoggerContext.put("user_id", 42)
        self.log.info("User booked room")
        with open(path, encoding="utf-8") as fh:
            payload = json.loads(fh.readline())
        for key in ("timestamp", "level", "req_id", "msg", "user_id"):
            self.assertIn(key, payload)
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["user_id"], 42)

    def test_rotation_creates_archive(self):
        """При достижении лимита файл архивируется, запись продолжается в новый."""
        path = os.path.join(self.tmp, "app.log")
        self.log.clear_sinks().add_sink(FileSink(path, max_bytes=2048))
        for i in range(120):
            self.log.info("наполнение файла записью номер {}", i)
        archives = [f for f in os.listdir(self.tmp) if f.startswith("app-")]
        self.assertGreaterEqual(len(archives), 1)
        self.assertTrue(os.path.exists(path))
        self.assertLess(os.path.getsize(path), 2048 * 3)

    def test_crash_report_receives_only_errors(self):
        """Администратору уходят только ERROR и FATAL."""
        path = os.path.join(self.tmp, "crash_report.txt")
        self.log.clear_sinks().add_sink(CrashReportSink(path))
        self.log.info("обычное событие")
        self.log.error("сбой записи брони")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("сбой записи брони", text)
        self.assertNotIn("обычное событие", text)

    def test_context_is_isolated_between_threads(self):
        """Метаданные разных потоков не перемешиваются."""
        seen = {}

        def worker(name):
            LoggerContext.put("req_id", name)
            seen[name] = LoggerContext.snapshot()["req_id"]

        threads = [threading.Thread(target=worker, args=("req-%d" % i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(seen, {"req-%d" % i: "req-%d" % i for i in range(5)})


class BookingFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.log = DebugManager.instance().clear_sinks()
        self.log.set_threshold(LogLevel.FATAL)
        self.store = BookingStore()

    def _run_load(self, unsafe):
        service = BookingService(self.store, unsafe=unsafe)
        barrier = threading.Barrier(THREADS)
        denied = []

        def worker(user_id):
            barrier.wait()
            try:
                service.book(ROOM, DAY, user_id)
            except QuotaExceeded:
                denied.append(user_id)

        threads = [threading.Thread(target=worker, args=(100 + i,)) for i in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return len(self.store.all()), len(denied)

    def test_quota_is_respected_in_fixed_version(self):
        """Требование: не более 5 броней на комнату в день."""
        saved, denied = self._run_load(unsafe=False)
        self.assertEqual(saved, QUOTA_PER_DAY)
        self.assertEqual(denied, THREADS - QUOTA_PER_DAY)

    def test_race_condition_reproduces_in_buggy_version(self):
        """Контрольный тест: исходная версия нарушает квоту."""
        saved, _ = self._run_load(unsafe=True)
        self.assertGreater(saved, QUOTA_PER_DAY)

    def test_single_booking_is_accepted(self):
        """Одиночная бронь проходит и сохраняется."""
        service = BookingService(self.store, unsafe=False)
        service.book(ROOM, DAY, 777)
        rows = self.store.all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["user"], 777)


if __name__ == "__main__":
    unittest.main(verbosity=2)
