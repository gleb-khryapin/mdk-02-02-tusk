"""LoggerContext - потокобезопасное хранилище метаданных запроса."""
import threading
import uuid


class LoggerContext:
    """Метаданные (ID пользователя, ID запроса) живут отдельно в каждом потоке.

    Используется threading.local: каждый поток видит только свой словарь,
    поэтому блокировки при чтении не нужны - гонки за данными нет по построению.
    """

    _local = threading.local()
    _lock = threading.Lock()
    _global = {}

    @classmethod
    def _store(cls):
        if not hasattr(cls._local, "data"):
            cls._local.data = {}
        return cls._local.data

    @classmethod
    def put(cls, key, value):
        cls._store()[key] = value

    @classmethod
    def get(cls, key, default=None):
        value = cls._store().get(key)
        if value is not None:
            return value
        with cls._lock:
            return cls._global.get(key, default)

    @classmethod
    def put_global(cls, key, value):
        with cls._lock:
            cls._global[key] = value

    @classmethod
    def snapshot(cls):
        with cls._lock:
            data = dict(cls._global)
        data.update(cls._store())
        data["thread"] = threading.current_thread().name
        return data

    @classmethod
    def clear(cls):
        cls._store().clear()

    @classmethod
    def new_request_id(cls):
        req_id = "req-" + uuid.uuid4().hex[:8]
        cls.put("req_id", req_id)
        return req_id
